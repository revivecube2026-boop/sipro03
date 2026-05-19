"""Extracted router for whatsapp (Phase F refactor)."""
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

# ==================== WHATSAPP ROUTES ====================

@router.get("/whatsapp/messages")
async def list_whatsapp_messages(request: Request, skip: int = 0, limit: int = 50):
    user = await get_current_user(request, db)
    total = await db.whatsapp_messages.count_documents({})
    messages = await db.whatsapp_messages.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"data": messages, "total": total}

@router.post("/whatsapp/send")
async def send_whatsapp_message(req: WhatsAppMessageCreate, request: Request):
    user = await get_current_user(request, db)
    msg_doc = {
        "id": str(uuid.uuid4()),
        "recipient_phone": req.recipient_phone,
        "recipient_name": req.recipient_name,
        "message": req.message,
        "message_type": req.message_type,
        "related_entity_type": req.related_entity_type,
        "related_entity_id": req.related_entity_id,
        "status": "queued",
        "sent_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.whatsapp_messages.insert_one(msg_doc)
    msg_doc.pop("_id", None)
    
    # In production, this would call WhatsApp Business API
    # For now, mark as sent (simulated)
    await db.whatsapp_messages.update_one({"id": msg_doc["id"]}, {"$set": {"status": "sent"}})
    msg_doc["status"] = "sent"
    
    return {"data": msg_doc}

@router.get("/whatsapp/templates")
async def list_whatsapp_templates(request: Request):
    user = await get_current_user(request, db)
    templates = await db.whatsapp_templates.find({}, {"_id": 0}).to_list(50)
    return {"data": templates}

