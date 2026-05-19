"""Cross-cutting helpers used by multiple routers."""
import re as _re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Response

from deps import db, COOKIE_SECURE, COOKIE_SAMESITE, logger


# ----- Phone normalization -----
def _normalize_phone(phone: Optional[str]) -> Optional[str]:
    """Normalize Indonesian phone numbers to E.164 (+62...). Idempotent."""
    if not phone:
        return None
    digits = _re.sub(r'[^\d+]', '', phone.strip())
    if not digits:
        return None
    if digits.startswith('+'):
        return digits
    if digits.startswith('62'):
        return '+' + digits
    if digits.startswith('0'):
        return '+62' + digits[1:]
    if digits.startswith('8'):
        return '+62' + digits
    return '+' + digits


async def _normalize_nik(nik: Optional[str]) -> Optional[str]:
    if not nik:
        return None
    digits = _re.sub(r'\D', '', nik)
    return digits or None


# ----- Strict RBAC scope -----
SCOPED_ROLES = {"sales", "marketing_inhouse"}


def _apply_lead_scope(user: dict, query: dict) -> dict:
    if user.get("role") in SCOPED_ROLES:
        query = {**query, "assigned_to": user.get("email")}
    return query


def _apply_task_scope(user: dict, query: dict) -> dict:
    if user.get("role") in SCOPED_ROLES:
        query = {**query, "assigned_to": user.get("email")}
    return query


def _apply_appointment_scope(user: dict, query: dict) -> dict:
    if user.get("role") in SCOPED_ROLES:
        query = {**query, "assigned_to": user.get("email")}
    return query


def _can_access_lead(user: dict, lead: dict) -> bool:
    if user.get("role") not in SCOPED_ROLES:
        return True
    return lead.get("assigned_to") == user.get("email")


# ----- Auth cookies -----
def _set_auth_cookies(response: Response, access_token: str, refresh_token: Optional[str] = None):
    response.set_cookie(
        key="access_token", value=access_token,
        httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE,
        max_age=86400, path="/",
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token", value=refresh_token,
            httponly=True, secure=COOKIE_SECURE, samesite=COOKIE_SAMESITE,
            max_age=604800, path="/",
        )


# ----- Time helpers -----
def _due_in(hours: int = 0, days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours, days=days)).isoformat()


# ----- Task auto-creation (cross-cutting) -----
async def _get_task_permissions():
    doc = await db.app_settings.find_one({"key": "tasks_permissions"}, {"_id": 0})
    if not doc:
        return ["super_admin", "marketing_admin", "marketing_inhouse", "sales"]
    return doc.get("allowed_roles") or []


async def _auto_create_task(
    *, title: str, type: str, source_event: str,
    related_entity_type: str, related_entity_id: str,
    assigned_to: Optional[str] = None, due_date: Optional[str] = None,
    description: Optional[str] = None, priority: str = "medium",
):
    """Idempotent auto-task creation. Skips if an OPEN task with same source_event exists."""
    existing = await db.tasks.find_one({
        "source_event": source_event,
        "status": {"$in": ["open", "in_progress", "snoozed"]},
    }, {"_id": 0, "id": 1})
    if existing:
        return None
    now = datetime.now(timezone.utc).isoformat()
    task_doc = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "type": type,
        "status": "open",
        "priority": priority,
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
        "assigned_to": assigned_to,
        "due_date": due_date,
        "source_event": source_event,
        "auto_generated": True,
        "outcome": None,
        "activity_history": [{"action": "auto_created", "by": "system", "at": now}],
        "created_by": "system",
        "created_at": now,
        "updated_at": now,
    }
    await db.tasks.insert_one(task_doc)
    task_doc.pop("_id", None)
    return task_doc


# ----- Customer auto-link (Phase E) -----
async def _find_or_create_customer_from_deal(deal: dict, user_email: str) -> Optional[str]:
    phone = _normalize_phone(deal.get("customer_phone"))
    name = deal.get("customer_name")
    if not phone and not name:
        return None
    query = {}
    if phone:
        query["phone"] = phone
    elif name:
        query["name"] = name
    existing = await db.customers.find_one(query, {"_id": 0, "id": 1})
    if existing:
        return existing["id"]
    now = datetime.now(timezone.utc).isoformat()
    cust = {
        "id": str(uuid.uuid4()),
        "name": name,
        "phone": phone,
        "email": (deal.get("customer_email") or "").lower() or None,
        "created_from": "deal_auto",
        "created_by": user_email,
        "created_at": now,
        "updated_at": now,
    }
    await db.customers.insert_one(cust)
    logger.info(f"Auto-created customer for deal {deal.get('id')}: {cust['id']}")
    return cust["id"]


# ----- Commission auto-create (Phase E) -----
def _calc_commission(rule: dict, deal_price: float) -> float:
    rt = rule.get("rate_type", "percent")
    if rt == "flat":
        return float(rule.get("rate_value") or 0)
    if rt == "tier":
        tiers = rule.get("tiers") or []
        for t in tiers:
            mn = t.get("min_amount", 0) or 0
            mx = t.get("max_amount") or float("inf")
            if mn <= deal_price < mx:
                return deal_price * (t.get("rate", 0) / 100.0)
        return 0.0
    return deal_price * (float(rule.get("rate_value") or 0) / 100.0)


async def _resolve_commission_rule(deal: dict, assignee_role: str) -> Optional[dict]:
    rules = await db.commission_rules.find({"is_active": True}, {"_id": 0}).to_list(200)
    candidates = []
    for r in rules:
        ok_project = (r.get("project_id") is None) or (r.get("project_id") == deal.get("project_id"))
        ok_role = (r.get("role") is None) or (r.get("role") == assignee_role)
        if ok_project and ok_role:
            specificity = (1 if r.get("project_id") else 0) + (1 if r.get("role") else 0)
            candidates.append((specificity, r.get("priority", 0), r))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]


async def _auto_create_commission(deal: dict, by: str):
    existing = await db.commissions.find_one({"deal_id": deal["id"]}, {"_id": 0, "id": 1})
    if existing:
        return None
    assignee = None
    assignee_role = None
    if deal.get("lead_id"):
        lead = await db.leads.find_one({"id": deal["lead_id"]}, {"_id": 0, "assigned_to": 1})
        if lead and lead.get("assigned_to"):
            assignee = lead["assigned_to"]
    if not assignee:
        assignee = deal.get("created_by")
    if assignee:
        u = await db.users.find_one({"email": assignee}, {"_id": 0, "role": 1})
        assignee_role = (u or {}).get("role")
    rule = await _resolve_commission_rule(deal, assignee_role)
    if not rule:
        return None
    amount = _calc_commission(rule, float(deal.get("price") or 0))
    if amount <= 0:
        return None
    now = datetime.now(timezone.utc).isoformat()
    comm = {
        "id": str(uuid.uuid4()),
        "deal_id": deal["id"],
        "unit_id": deal.get("unit_id"),
        "project_id": deal.get("project_id"),
        "customer_name": deal.get("customer_name"),
        "assignee_email": assignee,
        "assignee_role": assignee_role,
        "rule_id": rule["id"],
        "rule_name": rule.get("name"),
        "rate_type": rule.get("rate_type"),
        "rate_value": rule.get("rate_value"),
        "deal_price": float(deal.get("price") or 0),
        "amount": amount,
        "status": "pending",
        "payout_date": None,
        "reference": None,
        "notes": None,
        "created_by": by,
        "created_at": now,
        "updated_at": now,
    }
    await db.commissions.insert_one(comm)
    comm.pop("_id", None)
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "commission.created",
        "entity_type": "commission",
        "entity_id": comm["id"],
        "data": {"deal_id": deal["id"], "amount": amount, "assignee": assignee},
        "created_at": now,
    })
    return comm
