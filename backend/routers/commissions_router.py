"""Phase E — Commission Engine routes."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from deps import db, get_current_user
from shared import SCOPED_ROLES
from models import CommissionRuleCreate, CommissionRuleUpdate, CommissionPayout

router = APIRouter()


@router.get("/commissions/rules")
async def list_commission_rules(request: Request):
    await get_current_user(request, db)
    rules = await db.commission_rules.find({}, {"_id": 0}).sort("priority", -1).to_list(200)
    return {"data": rules}


@router.post("/commissions/rules")
async def create_commission_rule(req: CommissionRuleCreate, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "marketing_admin", "management"]:
        raise HTTPException(status_code=403, detail="Only admins can create commission rules")
    now = datetime.now(timezone.utc).isoformat()
    doc = req.dict()
    doc["id"] = str(uuid.uuid4())
    doc["created_by"] = user.get("email")
    doc["created_at"] = now
    doc["updated_at"] = now
    await db.commission_rules.insert_one(doc)
    doc.pop("_id", None)
    return {"data": doc}


@router.put("/commissions/rules/{rule_id}")
async def update_commission_rule(rule_id: str, req: CommissionRuleUpdate, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "marketing_admin", "management"]:
        raise HTTPException(status_code=403, detail="Only admins can edit commission rules")
    update_fields = {k: v for k, v in req.dict().items() if v is not None}
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.commission_rules.update_one({"id": rule_id}, {"$set": update_fields})
    return {"data": await db.commission_rules.find_one({"id": rule_id}, {"_id": 0})}


@router.delete("/commissions/rules/{rule_id}")
async def delete_commission_rule(rule_id: str, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "marketing_admin", "management"]:
        raise HTTPException(status_code=403, detail="Only admins can delete commission rules")
    await db.commission_rules.delete_one({"id": rule_id})
    return {"message": "deleted"}


@router.get("/commissions")
async def list_commissions(
    request: Request,
    assignee_email: Optional[str] = None,
    status: Optional[str] = None,
    deal_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    user = await get_current_user(request, db)
    query: dict = {}
    if assignee_email:
        query["assignee_email"] = assignee_email
    if status:
        query["status"] = status
    if deal_id:
        query["deal_id"] = deal_id
    if user.get("role") in SCOPED_ROLES:
        query["assignee_email"] = user.get("email")
    total = await db.commissions.count_documents(query)
    items = await db.commissions.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"data": items, "total": total}


@router.get("/commissions/stats")
async def commissions_stats(request: Request, assignee_email: Optional[str] = None):
    user = await get_current_user(request, db)
    base = {}
    if user.get("role") in SCOPED_ROLES:
        base["assignee_email"] = user.get("email")
    elif assignee_email:
        base["assignee_email"] = assignee_email

    async def _sum(q):
        agg = await db.commissions.aggregate([{"$match": q}, {"$group": {"_id": None, "t": {"$sum": "$amount"}, "c": {"$sum": 1}}}]).to_list(1)
        return (agg[0] if agg else {"t": 0, "c": 0})

    pending = await _sum({**base, "status": "pending"})
    approved = await _sum({**base, "status": "approved"})
    paid = await _sum({**base, "status": "paid"})
    return {"data": {
        "pending": {"amount": pending["t"], "count": pending["c"]},
        "approved": {"amount": approved["t"], "count": approved["c"]},
        "paid": {"amount": paid["t"], "count": paid["c"]},
    }}


@router.post("/commissions/{commission_id}/approve")
async def approve_commission(commission_id: str, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "marketing_admin", "management", "finance"]:
        raise HTTPException(status_code=403, detail="Only admins/finance can approve commission")
    now = datetime.now(timezone.utc).isoformat()
    await db.commissions.update_one({"id": commission_id}, {"$set": {"status": "approved", "approved_at": now, "approved_by": user.get("email"), "updated_at": now}})
    return {"data": await db.commissions.find_one({"id": commission_id}, {"_id": 0})}


@router.post("/commissions/{commission_id}/pay")
async def pay_commission(commission_id: str, req: CommissionPayout, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "finance", "management"]:
        raise HTTPException(status_code=403, detail="Only finance/admin can mark commission paid")
    now = datetime.now(timezone.utc).isoformat()
    await db.commissions.update_one({"id": commission_id}, {"$set": {
        "status": "paid", "payout_date": req.payout_date, "reference": req.reference, "notes": req.notes,
        "paid_at": now, "paid_by": user.get("email"), "updated_at": now,
    }})
    return {"data": await db.commissions.find_one({"id": commission_id}, {"_id": 0})}
