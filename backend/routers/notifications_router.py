"""Extracted router for notifications (Phase F refactor)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Query

from deps import db, get_current_user, COOKIE_SECURE, COOKIE_SAMESITE, BOOKING_HOLD_DAYS, logger
from shared import (
    _normalize_phone, _apply_lead_scope, _apply_task_scope, _apply_appointment_scope,
    _can_access_lead, _set_auth_cookies, _due_in, _auto_create_task,
    SCOPED_ROLES,
)
from models import *

router = APIRouter()

# ==================== NOTIFICATION CENTER ROUTES ====================

@router.get("/notifications")
async def list_notifications(request: Request, unread_only: bool = False, skip: int = 0, limit: int = 50):
    user = await get_current_user(request, db)
    query = {"$or": [{"target_user": user.get("email")}, {"target_user": None}, {"target_user": "all"}]}
    if unread_only:
        query["read"] = False
    total = await db.notifications.count_documents(query)
    notifs = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    unread = await db.notifications.count_documents({**query, "read": False})
    return {"data": notifs, "total": total, "unread": unread}

@router.post("/notifications")
async def create_notification(req: NotificationCreate, request: Request):
    user = await get_current_user(request, db)
    notif_doc = {
        "id": str(uuid.uuid4()),
        "title": req.title,
        "message": req.message,
        "type": req.type,
        "target_user": req.target_user or "all",
        "related_entity_type": req.related_entity_type,
        "related_entity_id": req.related_entity_id,
        "read": False,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notif_doc)
    notif_doc.pop("_id", None)
    return {"data": notif_doc}

@router.put("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, request: Request):
    user = await get_current_user(request, db)
    await db.notifications.update_one({"id": notif_id}, {"$set": {"read": True}})
    return {"message": "Marked as read"}

@router.put("/notifications/read-all")
async def mark_all_notifications_read(request: Request):
    user = await get_current_user(request, db)
    query = {"$or": [{"target_user": user.get("email")}, {"target_user": None}, {"target_user": "all"}]}
    await db.notifications.update_many(query, {"$set": {"read": True}})
    return {"message": "All marked as read"}

# ---- Auto Follow-Up Rules ----
@router.get("/notifications/auto-rules")
async def list_auto_followup_rules(request: Request):
    user = await get_current_user(request, db)
    rules = await db.auto_followup_rules.find({}, {"_id": 0}).to_list(50)
    return {"data": rules}

@router.post("/notifications/auto-rules")
async def create_auto_followup_rule(req: AutoFollowUpRuleCreate, request: Request):
    user = await get_current_user(request, db)
    rule_doc = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "trigger_event": req.trigger_event,
        "delay_minutes": req.delay_minutes,
        "message_template": req.message_template,
        "channel": req.channel,
        "is_active": req.is_active,
        "executions": 0,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.auto_followup_rules.insert_one(rule_doc)
    rule_doc.pop("_id", None)
    return {"data": rule_doc}

@router.put("/notifications/auto-rules/{rule_id}")
async def update_auto_followup_rule(rule_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body.pop("id", None)
    body.pop("_id", None)
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.auto_followup_rules.update_one({"id": rule_id}, {"$set": body})
    rule = await db.auto_followup_rules.find_one({"id": rule_id}, {"_id": 0})
    return {"data": rule}

@router.delete("/notifications/auto-rules/{rule_id}")
async def delete_auto_followup_rule(rule_id: str, request: Request):
    user = await get_current_user(request, db)
    await db.auto_followup_rules.delete_one({"id": rule_id})
    return {"message": "Rule deleted"}

@router.post("/notifications/simulate-followup")
async def simulate_auto_followup(request: Request):
    """Simulate auto-follow-up for new leads (enhancement: real-time auto-WA for new leads from ads)"""
    user = await get_current_user(request, db)
    body = await request.json()
    lead_id = body.get("lead_id")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Find active rules for lead.created
    rules = await db.auto_followup_rules.find({"trigger_event": "lead.created", "is_active": True}, {"_id": 0}).to_list(10)
    
    results = []
    for rule in rules:
        message = rule["message_template"].replace("{name}", lead.get("name", "")).replace("{source}", lead.get("source", "")).replace("{project}", lead.get("project_id", ""))
        
        if rule["channel"] == "whatsapp" and lead.get("phone"):
            msg_doc = {
                "id": str(uuid.uuid4()),
                "recipient_phone": lead["phone"],
                "recipient_name": lead["name"],
                "message": message,
                "message_type": "auto_follow_up",
                "related_entity_type": "lead",
                "related_entity_id": lead_id,
                "status": "sent",
                "sent_by": "auto_system",
                "auto_rule_id": rule["id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.whatsapp_messages.insert_one(msg_doc)
            msg_doc.pop("_id", None)
            results.append({"channel": "whatsapp", "rule": rule["name"], "message_id": msg_doc["id"]})
        
        # Create in-app notification
        notif_doc = {
            "id": str(uuid.uuid4()),
            "title": f"Auto Follow-Up: {lead['name']}",
            "message": message,
            "type": "follow_up",
            "target_user": lead.get("assigned_to") or "all",
            "related_entity_type": "lead",
            "related_entity_id": lead_id,
            "read": False,
            "created_by": "auto_system",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notif_doc)
        results.append({"channel": "in_app", "rule": rule["name"], "notification_id": notif_doc["id"]})
        
        # Increment execution count
        await db.auto_followup_rules.update_one({"id": rule["id"]}, {"$inc": {"executions": 1}})
    
    return {"data": {"lead": lead["name"], "rules_executed": len(rules), "results": results}}

