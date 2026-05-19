"""Phase E — Customer Master."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from deps import db, get_current_user
from shared import _normalize_phone, _normalize_nik, _find_or_create_customer_from_deal
from models import CustomerCreate, CustomerUpdate

router = APIRouter()


@router.get("/customers")
async def list_customers(request: Request, search: Optional[str] = None, skip: int = 0, limit: int = 50):
    await get_current_user(request, db)
    query: dict = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"nik": {"$regex": search, "$options": "i"}},
        ]
    total = await db.customers.count_documents(query)
    items = await db.customers.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    for c in items:
        c["deal_count"] = await db.deals.count_documents({"customer_id": c["id"]})
    return {"data": items, "total": total}


@router.post("/customers")
async def create_customer(req: CustomerCreate, request: Request):
    user = await get_current_user(request, db)
    phone = _normalize_phone(req.phone)
    nik = await _normalize_nik(req.nik)
    if phone:
        dup = await db.customers.find_one({"phone": phone}, {"_id": 0, "id": 1})
        if dup:
            raise HTTPException(status_code=400, detail=f"Customer with phone {phone} already exists")
    if nik:
        dup = await db.customers.find_one({"nik": nik}, {"_id": 0, "id": 1})
        if dup:
            raise HTTPException(status_code=400, detail=f"Customer with NIK {nik} already exists")
    now = datetime.now(timezone.utc).isoformat()
    doc = req.dict()
    doc["phone"] = phone
    doc["nik"] = nik
    doc["spouse_phone"] = _normalize_phone(req.spouse_phone)
    doc["heir_phone"] = _normalize_phone(req.heir_phone)
    doc["email"] = (req.email or "").lower() or None
    doc["id"] = str(uuid.uuid4())
    doc["created_from"] = "manual"
    doc["created_by"] = user.get("email")
    doc["created_at"] = now
    doc["updated_at"] = now
    await db.customers.insert_one(doc)
    doc.pop("_id", None)
    return {"data": doc}


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, request: Request):
    await get_current_user(request, db)
    c = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    deals = await db.deals.find({"customer_id": customer_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"data": {**c, "deals": deals}}


@router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, req: CustomerUpdate, request: Request):
    user = await get_current_user(request, db)
    existing = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")
    update_fields = {k: v for k, v in req.dict().items() if v is not None}
    if "phone" in update_fields:
        update_fields["phone"] = _normalize_phone(update_fields["phone"])
    if "nik" in update_fields:
        update_fields["nik"] = await _normalize_nik(update_fields["nik"])
    if "spouse_phone" in update_fields:
        update_fields["spouse_phone"] = _normalize_phone(update_fields["spouse_phone"])
    if "heir_phone" in update_fields:
        update_fields["heir_phone"] = _normalize_phone(update_fields["heir_phone"])
    if "email" in update_fields:
        update_fields["email"] = (update_fields["email"] or "").lower() or None
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_fields["updated_by"] = user.get("email")
    await db.customers.update_one({"id": customer_id}, {"$set": update_fields})
    return {"data": await db.customers.find_one({"id": customer_id}, {"_id": 0})}


@router.post("/customers/backfill")
async def backfill_customers(request: Request):
    """Phase E: scan existing deals, group by phone, create customer doc & link customer_id."""
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "marketing_admin", "management"]:
        raise HTTPException(status_code=403, detail="Only admins can backfill customers")
    deals = await db.deals.find({"customer_id": {"$in": [None, ""]}}, {"_id": 0}).to_list(2000)
    deals_no_field = await db.deals.find({"customer_id": {"$exists": False}}, {"_id": 0}).to_list(2000)
    seen = {d["id"] for d in deals}
    for d in deals_no_field:
        if d["id"] not in seen:
            deals.append(d)
    created = 0
    linked = 0
    for d in deals:
        cust_id = await _find_or_create_customer_from_deal(d, user.get("email"))
        if cust_id:
            await db.deals.update_one({"id": d["id"]}, {"$set": {"customer_id": cust_id}})
            linked += 1
            c = await db.customers.find_one({"id": cust_id}, {"_id": 0, "created_from": 1})
            if c and c.get("created_from") == "deal_auto":
                created += 1
    return {"data": {"deals_processed": len(deals), "linked": linked, "customers_created_or_linked": created}}
