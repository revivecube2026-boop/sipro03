"""Extracted router for dev_report (Phase F refactor)."""
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

# ==================== DEVELOPMENT REPORT ROUTES ====================

@router.get("/dev-report")
async def get_dev_report(request: Request):
    user = await get_current_user(request, db)
    items = await db.dev_report_items.find({}, {"_id": 0}).sort("module", 1).to_list(500)
    
    total = len(items)
    completed = sum(1 for i in items if i.get("status") == "completed")
    in_progress = sum(1 for i in items if i.get("status") == "in_progress")
    not_started = sum(1 for i in items if i.get("status") == "not_started")
    
    report = await db.dev_report_meta.find_one({"type": "meta"}, {"_id": 0})
    
    return {
        "data": {
            "items": items,
            "summary": {"total": total, "completed": completed, "in_progress": in_progress, "not_started": not_started},
            "meta": report or {"last_updated": None, "notes": ""}
        }
    }

@router.post("/dev-report/items")
async def create_dev_report_item(req: DevReportItemCreate, request: Request):
    user = await get_current_user(request, db)
    item_doc = {
        "id": str(uuid.uuid4()),
        "module": req.module,
        "feature": req.feature,
        "status": req.status,
        "priority": req.priority,
        "notes": req.notes,
        "milestone": req.milestone,
        "blockers": req.blockers,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.dev_report_items.insert_one(item_doc)
    item_doc.pop("_id", None)
    return {"data": item_doc}

@router.put("/dev-report/items/{item_id}")
async def update_dev_report_item(item_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("id", None)
    body.pop("_id", None)
    await db.dev_report_items.update_one({"id": item_id}, {"$set": body})
    item = await db.dev_report_items.find_one({"id": item_id}, {"_id": 0})
    return {"data": item}

@router.delete("/dev-report/items/{item_id}")
async def delete_dev_report_item(item_id: str, request: Request):
    user = await get_current_user(request, db)
    await db.dev_report_items.delete_one({"id": item_id})
    return {"message": "Item deleted"}

@router.put("/dev-report/meta")
async def update_dev_report_meta(request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["type"] = "meta"
    body["updated_by"] = user.get("email")
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.dev_report_meta.update_one({"type": "meta"}, {"$set": body}, upsert=True)
    return {"data": body}

