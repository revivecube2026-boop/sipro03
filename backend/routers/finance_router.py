"""Extracted router for finance (Phase F refactor)."""
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

# ==================== FINANCE ROUTES ====================

@router.get("/finance/billing")
async def list_billing_schedules(request: Request, deal_id: Optional[str] = None, project_id: Optional[str] = None, status: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if deal_id: query["deal_id"] = deal_id
    if project_id: query["project_id"] = project_id
    if status: query["items.status"] = status
    schedules = await db.billing_schedules.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"data": schedules}

@router.post("/finance/billing")
async def create_billing_schedule(req: BillingScheduleCreate, request: Request):
    user = await get_current_user(request, db)
    billing_doc = {
        "id": str(uuid.uuid4()),
        "deal_id": req.deal_id,
        "unit_id": req.unit_id,
        "project_id": req.project_id,
        "customer_name": req.customer_name,
        "items": [],
        "total_amount": 0,
        "paid_amount": 0,
        "outstanding": 0,
        "status": "active",
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    # Generate billing items from items list
    for item in req.items:
        billing_item = {
            "id": str(uuid.uuid4()),
            "description": item.get("description", ""),
            "amount": item.get("amount", 0),
            "due_date": item.get("due_date", ""),
            "status": "pending",
            "paid_amount": 0
        }
        billing_doc["items"].append(billing_item)
        billing_doc["total_amount"] += billing_item["amount"]
    billing_doc["outstanding"] = billing_doc["total_amount"]
    
    await db.billing_schedules.insert_one(billing_doc)
    billing_doc.pop("_id", None)
    return {"data": billing_doc}

@router.post("/finance/payments")
async def record_payment(req: PaymentCreate, request: Request):
    user = await get_current_user(request, db)
    payment_doc = {
        "id": str(uuid.uuid4()),
        "deal_id": req.deal_id,
        "billing_item_id": req.billing_item_id,
        "amount": req.amount,
        "payment_date": req.payment_date,
        "payment_method": req.payment_method,
        "reference": req.reference,
        "notes": req.notes,
        "status": "confirmed",
        "recorded_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payments.insert_one(payment_doc)
    payment_doc.pop("_id", None)
    
    # Update billing schedule
    if req.billing_item_id:
        billing = await db.billing_schedules.find_one({"items.id": req.billing_item_id})
        if billing:
            for item in billing.get("items", []):
                if item["id"] == req.billing_item_id:
                    item["paid_amount"] = item.get("paid_amount", 0) + req.amount
                    if item["paid_amount"] >= item["amount"]:
                        item["status"] = "paid"
                    else:
                        item["status"] = "partial"
            paid_total = sum(i.get("paid_amount", 0) for i in billing["items"])
            await db.billing_schedules.update_one(
                {"id": billing["id"]},
                {"$set": {"items": billing["items"], "paid_amount": paid_total, "outstanding": billing["total_amount"] - paid_total, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
    
    # Update unit payment status
    deal = await db.deals.find_one({"id": req.deal_id}, {"_id": 0})
    if deal:
        billing = await db.billing_schedules.find_one({"deal_id": req.deal_id}, {"_id": 0})
        if billing:
            pstatus = "dp_paid"
            if billing["paid_amount"] >= billing["total_amount"]:
                pstatus = "paid_off"
            elif any(i.get("status") == "overdue" for i in billing.get("items", [])):
                pstatus = "overdue"
            elif billing["paid_amount"] > 0:
                pstatus = "installment"
            await db.units.update_one({"id": deal["unit_id"]}, {"$set": {"payment_status": pstatus}})
    
    await db.events.insert_one({
        "id": str(uuid.uuid4()), "type": "payment.completed",
        "entity_type": "payment", "entity_id": payment_doc["id"],
        "data": {"deal_id": req.deal_id, "amount": req.amount},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"data": payment_doc}

@router.get("/finance/payments")
async def list_payments(request: Request, deal_id: Optional[str] = None, skip: int = 0, limit: int = 100):
    user = await get_current_user(request, db)
    query = {}
    if deal_id: query["deal_id"] = deal_id
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.payments.count_documents(query)
    return {"data": payments, "total": total}

@router.get("/finance/summary")
async def finance_summary(request: Request):
    user = await get_current_user(request, db)
    total_billing = await db.billing_schedules.count_documents({})
    pipeline_total = [{"$group": {"_id": None, "total": {"$sum": "$total_amount"}, "paid": {"$sum": "$paid_amount"}, "outstanding": {"$sum": "$outstanding"}}}]
    agg = await db.billing_schedules.aggregate(pipeline_total).to_list(1)
    amounts = agg[0] if agg else {"total": 0, "paid": 0, "outstanding": 0}
    total_payments = await db.payments.count_documents({})
    overdue_items = 0
    all_billings = await db.billing_schedules.find({}, {"_id": 0, "items": 1}).to_list(500)
    now = datetime.now(timezone.utc).isoformat()
    for b in all_billings:
        for item in b.get("items", []):
            if item.get("status") == "pending" and item.get("due_date") and item["due_date"] < now:
                overdue_items += 1
    return {"data": {
        "total_billing": total_billing, "total_amount": amounts["total"],
        "paid_amount": amounts["paid"], "outstanding": amounts["outstanding"],
        "total_payments": total_payments, "overdue_items": overdue_items
    }}

