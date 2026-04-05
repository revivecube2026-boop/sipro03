from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, UploadFile, File, Query
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import json

from auth import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, get_current_user, get_jwt_secret,
    generate_reset_token, JWT_ALGORITHM
)
import jwt as pyjwt

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="SIPRO - Property Development OS")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== PYDANTIC MODELS ====================

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "sales"

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class OrganizationCreate(BaseModel):
    name: str
    type: str = "developer"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class ProjectCreate(BaseModel):
    name: str
    organization_id: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    total_units: int = 0
    target_revenue: float = 0
    status: str = "planning"

class UnitCreate(BaseModel):
    project_id: str
    block: str = ""
    number: str = ""
    unit_type: str = "standard"
    floor_area: float = 0
    land_area: float = 0
    price: float = 0
    status: str = "available"
    coordinates: Optional[dict] = None

class LeadCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    source: str = "manual"
    campaign: Optional[str] = None
    ad_set: Optional[str] = None
    ad_name: Optional[str] = None
    notes: Optional[str] = None
    project_id: Optional[str] = None
    assigned_to: Optional[str] = None
    stage: Optional[str] = None  # acquisition, nurturing, appointment, booking, recycle

class LeadAssignRequest(BaseModel):
    lead_ids: List[str]
    assigned_to: str
    reason: Optional[str] = None

class LeadAssignmentResponse(BaseModel):
    lead_id: str
    action: str  # accept, reject
    reason: Optional[str] = None

class LeadActivityCreate(BaseModel):
    lead_id: str
    type: str  # call, chat, meeting, site_visit, note, reminder
    description: str
    outcome: Optional[str] = None

class AppointmentCreate(BaseModel):
    lead_id: str
    project_id: Optional[str] = None
    scheduled_at: str
    location: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None

class DealCreate(BaseModel):
    lead_id: Optional[str] = None
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    unit_id: str
    project_id: str
    price: float
    payment_method: str = "cash"
    notes: Optional[str] = None

class WhatsAppMessageCreate(BaseModel):
    recipient_phone: str
    recipient_name: Optional[str] = None
    message: str
    message_type: str = "notification"
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None

class DevReportItemCreate(BaseModel):
    module: str
    feature: str
    status: str = "not_started"  # not_started, in_progress, completed
    priority: str = "medium"
    notes: Optional[str] = None
    milestone: Optional[str] = None
    blockers: Optional[str] = None

class SiteplanNodeCreate(BaseModel):
    project_id: str
    unit_id: Optional[str] = None
    label: str
    x: float = 0
    y: float = 0
    width: float = 60
    height: float = 40
    shape: str = "rect"
    rotation: float = 0

# ---- Finance Models ----
class BillingScheduleCreate(BaseModel):
    deal_id: str
    unit_id: str
    project_id: str
    customer_name: str
    items: List[dict] = []  # [{description, amount, due_date, status}]

class PaymentCreate(BaseModel):
    deal_id: str
    billing_item_id: Optional[str] = None
    amount: float
    payment_date: str
    payment_method: str = "transfer"
    reference: Optional[str] = None
    notes: Optional[str] = None

# ---- Construction Models ----
class ConstructionPhaseCreate(BaseModel):
    project_id: str
    unit_id: str
    phase_name: str
    weight: float = 0  # percentage weight
    tasks: List[dict] = []  # [{name, weight, status}]

class ConstructionProgressUpdate(BaseModel):
    unit_id: str
    phase_id: str
    task_id: Optional[str] = None
    status: str  # not_started, in_progress, qc_pending, passed, failed, rework, completed
    notes: Optional[str] = None
    photo_url: Optional[str] = None

# ---- Notification Models ----
class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "info"  # info, success, warning, danger, follow_up
    target_user: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None

class AutoFollowUpRuleCreate(BaseModel):
    name: str
    trigger_event: str  # lead.created, appointment.no_show, payment.overdue
    delay_minutes: int = 5
    message_template: str
    channel: str = "whatsapp"  # whatsapp, in_app
    is_active: bool = True

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register")
async def register(req: RegisterRequest, response: Response):
    email = req.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "email": email,
        "password_hash": hash_password(req.password),
        "name": req.name,
        "role": req.role,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email, req.role)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=86400, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {"id": user_id, "email": email, "name": req.name, "role": req.role, "token": access_token}

@api_router.post("/auth/login")
async def login(req: LoginRequest, request: Request, response: Response):
    email = req.email.lower().strip()
    ip = request.client.host if request.client else "unknown"
    identifier = f"{ip}:{email}"
    
    # Check brute force
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        locked_until = attempt.get("locked_until")
        if locked_until and datetime.fromisoformat(locked_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 15 minutes.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(req.password, user["password_hash"]):
        # Increment failed attempts
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"locked_until": (datetime.now(timezone.utc) + __import__('datetime').timedelta(minutes=15)).isoformat()}},
            upsert=True
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Clear failed attempts
    await db.login_attempts.delete_one({"identifier": identifier})
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email, user.get("role", "user"))
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=86400, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id, "email": user["email"], "name": user.get("name", ""),
        "role": user.get("role", "user"), "token": access_token
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request, db)
    return user

@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = pyjwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = str(user["_id"])
        access_token = create_access_token(user_id, user["email"], user.get("role", "user"))
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=86400, path="/")
        return {"message": "Token refreshed", "token": access_token}
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# ==================== ORGANIZATION ROUTES ====================

@api_router.get("/organizations")
async def list_organizations(request: Request):
    user = await get_current_user(request, db)
    orgs = await db.organizations.find({}, {"_id": 0}).to_list(100)
    return {"data": orgs}

@api_router.post("/organizations")
async def create_organization(req: OrganizationCreate, request: Request):
    user = await get_current_user(request, db)
    org_doc = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "type": req.type,
        "address": req.address,
        "phone": req.phone,
        "email": req.email,
        "status": "active",
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.organizations.insert_one(org_doc)
    org_doc.pop("_id", None)
    return {"data": org_doc}

# ==================== USER MANAGEMENT ROUTES ====================

@api_router.get("/users")
async def list_users(request: Request):
    user = await get_current_user(request, db)
    users = await db.users.find({}, {"password_hash": 0}).to_list(500)
    for u in users:
        u["_id"] = str(u["_id"])
    return {"data": users}

# ==================== PROJECT ROUTES ====================

@api_router.get("/projects")
async def list_projects(request: Request, status: Optional[str] = None, search: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if status:
        query["status"] = status
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    projects = await db.projects.find(query, {"_id": 0}).to_list(100)
    return {"data": projects}

@api_router.post("/projects")
async def create_project(req: ProjectCreate, request: Request):
    user = await get_current_user(request, db)
    project_doc = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "organization_id": req.organization_id,
        "location": req.location,
        "description": req.description,
        "total_units": req.total_units,
        "target_revenue": req.target_revenue,
        "status": req.status,
        "units_sold": 0,
        "units_available": req.total_units,
        "units_reserved": 0,
        "revenue_realized": 0,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.projects.insert_one(project_doc)
    project_doc.pop("_id", None)
    return {"data": project_doc}

@api_router.get("/projects/{project_id}")
async def get_project(project_id: str, request: Request):
    user = await get_current_user(request, db)
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"data": project}

@api_router.put("/projects/{project_id}")
async def update_project(project_id: str, req: ProjectCreate, request: Request):
    user = await get_current_user(request, db)
    update_data = req.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.projects.update_one({"id": project_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    return {"data": project}

@api_router.post("/projects/{project_id}/generate-units")
async def generate_units(project_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    blocks = body.get("blocks", [])
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    units_created = []
    for block_config in blocks:
        block_name = block_config.get("block", "A")
        count = block_config.get("count", 10)
        unit_type = block_config.get("unit_type", "standard")
        base_price = block_config.get("base_price", 500000000)
        land_area = block_config.get("land_area", 72)
        floor_area = block_config.get("floor_area", 36)
        
        for i in range(1, count + 1):
            unit_doc = {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "block": block_name,
                "number": str(i),
                "label": f"{block_name}-{i}",
                "unit_type": unit_type,
                "floor_area": floor_area,
                "land_area": land_area,
                "price": base_price,
                "status": "available",
                "deal_status": None,
                "construction_status": "not_started",
                "payment_status": None,
                "coordinates": {"x": ((i-1) % 5) * 70 + 20, "y": ((i-1) // 5) * 50 + 20},
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.units.insert_one(unit_doc)
            unit_doc.pop("_id", None)
            units_created.append(unit_doc)
    
    # Update project total
    total = await db.units.count_documents({"project_id": project_id})
    await db.projects.update_one({"id": project_id}, {"$set": {"total_units": total, "units_available": total}})
    
    return {"data": units_created, "count": len(units_created)}

# ==================== UNIT ROUTES ====================

@api_router.get("/units")
async def list_units(
    request: Request,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    block: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    user = await get_current_user(request, db)
    query = {}
    if project_id:
        query["project_id"] = project_id
    if status:
        query["status"] = status
    if block:
        query["block"] = block
    if search:
        query["label"] = {"$regex": search, "$options": "i"}
    
    total = await db.units.count_documents(query)
    units = await db.units.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    return {"data": units, "total": total, "skip": skip, "limit": limit}

@api_router.get("/units/{unit_id}")
async def get_unit(unit_id: str, request: Request):
    user = await get_current_user(request, db)
    unit = await db.units.find_one({"id": unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return {"data": unit}

@api_router.put("/units/{unit_id}")
async def update_unit(unit_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("id", None)
    body.pop("_id", None)
    result = await db.units.update_one({"id": unit_id}, {"$set": body})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Unit not found")
    unit = await db.units.find_one({"id": unit_id}, {"_id": 0})
    return {"data": unit}

@api_router.get("/units/{unit_id}/summary")
async def get_unit_summary(unit_id: str, request: Request):
    user = await get_current_user(request, db)
    unit = await db.units.find_one({"id": unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    deal = await db.deals.find_one({"unit_id": unit_id, "status": {"$nin": ["canceled", "expired", "failed"]}}, {"_id": 0})
    activities = await db.lead_activities.find({"unit_id": unit_id}, {"_id": 0}).sort("created_at", -1).to_list(5)
    return {"data": {"unit": unit, "deal": deal, "recent_activities": activities}}

# ==================== CRM / LEAD ROUTES ====================

@api_router.get("/leads")
async def list_leads(
    request: Request,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    source: Optional[str] = None,
    project_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    user = await get_current_user(request, db)
    query = {}
    if status:
        query["status"] = status
    if stage:
        query["stage"] = stage
    if source:
        query["source"] = source
    if project_id:
        query["project_id"] = project_id
    if assigned_to:
        query["assigned_to"] = assigned_to
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.leads.count_documents(query)
    leads = await db.leads.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Fallback: ensure stage exists on returned leads
    status_to_stage = {"new": "acquisition", "contacted": "nurturing", "prospect": "appointment", "no_response": "recycle", "lost": "recycle"}
    for lead in leads:
        if not lead.get("stage"):
            lead["stage"] = status_to_stage.get(lead.get("status", "new"), "acquisition")
    
    return {"data": leads, "total": total}

@api_router.get("/leads/pipeline")
async def get_lead_pipeline_inline(request: Request, project_id: Optional[str] = None):
    """Get lead funnel metrics — placed before /leads/{lead_id} to avoid route conflict"""
    user = await get_current_user(request, db)
    query = {}
    if project_id:
        query["project_id"] = project_id
    stages = ["acquisition", "nurturing", "appointment", "booking", "recycle"]
    pipeline_data = {}
    for stage in stages:
        pipeline_data[stage] = await db.leads.count_documents({**query, "stage": stage})
    total = sum(pipeline_data.values()) or 1
    return {"data": {
        "stages": pipeline_data,
        "total": total,
        "funnel": [{"stage": s, "count": pipeline_data[s], "pct": round(pipeline_data[s] / total * 100)} for s in stages]
    }}

@api_router.get("/leads/response-stats")
async def get_lead_response_stats(request: Request):
    """Get lead response time statistics for dashboard enhancement"""
    await get_current_user(request, db)
    
    pipeline = [
        {"$match": {"response_time_minutes": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": None,
            "avg_response_minutes": {"$avg": "$response_time_minutes"},
            "min_response_minutes": {"$min": "$response_time_minutes"},
            "max_response_minutes": {"$max": "$response_time_minutes"},
            "count": {"$sum": 1}
        }}
    ]
    stats = await db.leads.aggregate(pipeline).to_list(1)
    
    waiting = await db.leads.count_documents({"stage": "acquisition", "$or": [{"follow_up_count": 0}, {"follow_up_count": None}]})
    
    uncontacted_pipeline = [
        {"$match": {"stage": "acquisition", "$or": [{"follow_up_count": 0}, {"follow_up_count": None}]}},
        {"$project": {"created_at": 1}}
    ]
    uncontacted = await db.leads.aggregate(uncontacted_pipeline).to_list(100)
    now_dt = datetime.now(timezone.utc)
    avg_wait = 0
    if uncontacted:
        total_wait = 0
        for lead_item in uncontacted:
            try:
                created_dt = datetime.fromisoformat(lead_item["created_at"].replace('Z', '+00:00'))
                total_wait += (now_dt - created_dt).total_seconds() / 60
            except Exception:
                pass
        avg_wait = total_wait / len(uncontacted) if uncontacted else 0
    
    stat_result = stats[0] if stats else {"avg_response_minutes": 0, "min_response_minutes": 0, "max_response_minutes": 0, "count": 0}
    stat_result.pop("_id", None)
    stat_result["waiting_for_contact"] = waiting
    stat_result["avg_wait_minutes"] = round(avg_wait)
    
    return {"data": stat_result}

@api_router.post("/leads")
async def create_lead(req: LeadCreate, request: Request):
    user = await get_current_user(request, db)
    
    # Duplicate check
    if req.phone:
        dup = await db.leads.find_one({"phone": req.phone})
        if dup:
            raise HTTPException(status_code=400, detail=f"Lead with phone {req.phone} already exists")
    if req.email:
        dup = await db.leads.find_one({"email": req.email.lower()})
        if dup:
            raise HTTPException(status_code=400, detail=f"Lead with email {req.email} already exists")
    
    lead_doc = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "phone": req.phone,
        "email": req.email.lower() if req.email else None,
        "source": req.source,
        "campaign": req.campaign,
        "ad_set": req.ad_set,
        "ad_name": req.ad_name,
        "notes": req.notes,
        "project_id": req.project_id,
        "assigned_to": req.assigned_to,
        "status": "new",
        "stage": req.stage or "acquisition",
        "quality_score": 0,
        "follow_up_count": 0,
        "last_contacted_at": None,
        "nurturing_outcome": None,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.leads.insert_one(lead_doc)
    lead_doc.pop("_id", None)
    
    # Log event
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "lead.created",
        "entity_type": "lead",
        "entity_id": lead_doc["id"],
        "data": {"name": req.name, "source": req.source},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"data": lead_doc}

@api_router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("id", None)
    body.pop("_id", None)
    
    old_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not old_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Stage-first lifecycle: stage is the primary field
    # If stage is explicitly set, it takes priority
    # If only status changes, auto-map to stage as backward-compatible fallback
    if body.get("stage"):
        # Stage explicitly set - this is the primary lifecycle driver
        pass
    elif body.get("status") and body["status"] != old_lead.get("status"):
        # Status changed without explicit stage - map to stage for consistency
        status_to_stage = {"new": "acquisition", "contacted": "nurturing", "prospect": "appointment", "no_response": "recycle", "lost": "recycle"}
        new_stage = status_to_stage.get(body["status"])
        if new_stage:
            body["stage"] = new_stage
            logger.info(f"Lead {lead_id}: auto-mapped status '{body['status']}' to stage '{new_stage}'")
    
    # Ensure stage is always present after update
    if not body.get("stage") and not old_lead.get("stage"):
        body["stage"] = "acquisition"
        logger.warning(f"Lead {lead_id}: missing stage, defaulting to 'acquisition'")
    
    # Track follow-up count if status changes to contacted
    if body.get("status") == "contacted" and old_lead.get("status") != "contacted":
        body["follow_up_count"] = (old_lead.get("follow_up_count") or 0) + 1
        body["last_contacted_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.leads.update_one({"id": lead_id}, {"$set": body})
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    
    # Log status change
    if body.get("status") and body["status"] != old_lead.get("status"):
        await db.events.insert_one({
            "id": str(uuid.uuid4()),
            "type": "lead.status_changed",
            "entity_type": "lead",
            "entity_id": lead_id,
            "data": {"from": old_lead.get("status"), "to": body["status"], "stage": body.get("stage", old_lead.get("stage"))},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Log stage change
    if body.get("stage") and body["stage"] != old_lead.get("stage"):
        await db.events.insert_one({
            "id": str(uuid.uuid4()),
            "type": "lead.stage_changed",
            "entity_type": "lead",
            "entity_id": lead_id,
            "data": {"from_stage": old_lead.get("stage"), "to_stage": body["stage"]},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"data": lead}

@api_router.get("/leads/{lead_id}")
async def get_lead(lead_id: str, request: Request):
    user = await get_current_user(request, db)
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    activities = await db.lead_activities.find({"lead_id": lead_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    appointments = await db.appointments.find({"lead_id": lead_id}, {"_id": 0}).sort("scheduled_at", -1).to_list(20)
    return {"data": {**lead, "activities": activities, "appointments": appointments}}

@api_router.post("/leads/{lead_id}/activities")
async def create_lead_activity(lead_id: str, req: LeadActivityCreate, request: Request):
    user = await get_current_user(request, db)
    activity_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": lead_id,
        "type": req.type,
        "description": req.description,
        "outcome": req.outcome,
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.lead_activities.insert_one(activity_doc)
    activity_doc.pop("_id", None)
    return {"data": activity_doc}

# ==================== LEAD IMPORT ROUTES ====================

@api_router.post("/leads/import")
async def import_leads(request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    leads_data = body.get("leads", [])
    source = body.get("source", "csv_import")
    campaign = body.get("campaign", "")
    
    imported = 0
    duplicates = 0
    errors = []
    
    for idx, lead_data in enumerate(leads_data):
        try:
            name = lead_data.get("name", "").strip()
            phone = lead_data.get("phone", "").strip()
            email = (lead_data.get("email", "") or "").lower().strip()
            
            if not name:
                errors.append({"row": idx + 1, "error": "Name is required"})
                continue
            
            # Duplicate check
            dup_query = []
            if phone:
                dup_query.append({"phone": phone})
            if email:
                dup_query.append({"email": email})
            
            if dup_query:
                existing = await db.leads.find_one({"$or": dup_query})
                if existing:
                    duplicates += 1
                    continue
            
            lead_doc = {
                "id": str(uuid.uuid4()),
                "name": name,
                "phone": phone or None,
                "email": email or None,
                "source": source,
                "campaign": campaign,
                "ad_set": lead_data.get("ad_set", ""),
                "ad_name": lead_data.get("ad_name", ""),
                "notes": lead_data.get("notes", ""),
                "project_id": lead_data.get("project_id"),
                "assigned_to": None,
                "status": "new",
                "stage": "acquisition",
                "quality_score": 0,
                "follow_up_count": 0,
                "last_contacted_at": None,
                "nurturing_outcome": None,
                "import_batch": body.get("batch_id", str(uuid.uuid4())),
                "created_by": user.get("email"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.leads.insert_one(lead_doc)
            imported += 1
        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})
    
    # Log import event
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "leads.imported",
        "entity_type": "lead_import",
        "data": {"source": source, "imported": imported, "duplicates": duplicates, "errors": len(errors)},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"data": {"imported": imported, "duplicates": duplicates, "errors": errors}}

# ==================== LEAD ASSIGNMENT ROUTES ====================

@api_router.post("/leads/assign")
async def assign_leads(req: LeadAssignRequest, request: Request):
    """Manual assign leads to a user"""
    user = await get_current_user(request, db)
    now = datetime.now(timezone.utc).isoformat()
    
    # Verify target user exists
    target_user = await db.users.find_one({"email": req.assigned_to}, {"_id": 0, "email": 1, "name": 1, "role": 1})
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {req.assigned_to} not found")
    
    assigned_count = 0
    for lead_id in req.lead_ids:
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
        if not lead:
            continue
        
        old_assignee = lead.get("assigned_to")
        history_entry = {
            "from": old_assignee,
            "to": req.assigned_to,
            "assigned_by": user.get("email"),
            "reason": req.reason,
            "action": "assigned",
            "timestamp": now
        }
        
        await db.leads.update_one({"id": lead_id}, {
            "$set": {
                "assigned_to": req.assigned_to,
                "assignment_status": "pending",
                "updated_at": now
            },
            "$push": {"assignment_history": history_entry}
        })
        
        # Log event
        await db.events.insert_one({
            "id": str(uuid.uuid4()),
            "type": "lead.assigned",
            "entity_type": "lead",
            "entity_id": lead_id,
            "data": {"from": old_assignee, "to": req.assigned_to, "by": user.get("email"), "reason": req.reason},
            "created_at": now
        })
        assigned_count += 1
    
    return {"data": {"assigned": assigned_count, "target": req.assigned_to}}

@api_router.post("/leads/auto-assign")
async def auto_assign_leads(request: Request):
    """Round-robin auto-assign unassigned leads to marketing inhouse users"""
    user = await get_current_user(request, db)
    body = await request.json()
    stage = body.get("stage", "acquisition")
    role_filter = body.get("role", "sales")
    now = datetime.now(timezone.utc).isoformat()
    
    # Get eligible users (marketing inhouse / sales)
    eligible_roles = ["sales", "marketing_inhouse"]
    eligible_users = await db.users.find(
        {"role": {"$in": eligible_roles}, "status": "active"},
        {"_id": 0, "email": 1, "name": 1}
    ).to_list(100)
    
    if not eligible_users:
        raise HTTPException(status_code=400, detail="No eligible users for auto-assignment")
    
    # Get unassigned leads in the specified stage
    unassigned = await db.leads.find(
        {"$or": [{"assigned_to": None}, {"assigned_to": ""}], "stage": stage},
        {"_id": 0, "id": 1}
    ).to_list(500)
    
    if not unassigned:
        return {"data": {"assigned": 0, "message": "No unassigned leads found"}}
    
    # Round-robin assignment
    assigned_count = 0
    for i, lead in enumerate(unassigned):
        target = eligible_users[i % len(eligible_users)]
        history_entry = {
            "from": None,
            "to": target["email"],
            "assigned_by": "system:auto-assign",
            "reason": "Round-robin auto-assignment",
            "action": "auto_assigned",
            "timestamp": now
        }
        await db.leads.update_one({"id": lead["id"]}, {
            "$set": {
                "assigned_to": target["email"],
                "assignment_status": "pending",
                "updated_at": now
            },
            "$push": {"assignment_history": history_entry}
        })
        await db.events.insert_one({
            "id": str(uuid.uuid4()),
            "type": "lead.auto_assigned",
            "entity_type": "lead",
            "entity_id": lead["id"],
            "data": {"to": target["email"], "method": "round_robin"},
            "created_at": now
        })
        assigned_count += 1
    
    return {"data": {"assigned": assigned_count, "users": [u["email"] for u in eligible_users]}}

@api_router.post("/leads/{lead_id}/assignment/respond")
async def respond_to_assignment(lead_id: str, req: LeadAssignmentResponse, request: Request):
    """Accept or reject a lead assignment"""
    user = await get_current_user(request, db)
    now = datetime.now(timezone.utc).isoformat()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.get("assigned_to") != user.get("email"):
        raise HTTPException(status_code=403, detail="You are not the assigned user for this lead")
    
    if req.action == "accept":
        history_entry = {
            "from": user.get("email"),
            "to": user.get("email"),
            "assigned_by": user.get("email"),
            "reason": "Accepted",
            "action": "accepted",
            "timestamp": now
        }
        await db.leads.update_one({"id": lead_id}, {
            "$set": {"assignment_status": "accepted", "updated_at": now},
            "$push": {"assignment_history": history_entry}
        })
        await db.events.insert_one({
            "id": str(uuid.uuid4()),
            "type": "lead.assignment_accepted",
            "entity_type": "lead",
            "entity_id": lead_id,
            "data": {"user": user.get("email")},
            "created_at": now
        })
    elif req.action == "reject":
        history_entry = {
            "from": user.get("email"),
            "to": None,
            "assigned_by": user.get("email"),
            "reason": req.reason or "Rejected",
            "action": "rejected",
            "timestamp": now
        }
        await db.leads.update_one({"id": lead_id}, {
            "$set": {"assigned_to": None, "assignment_status": "rejected", "updated_at": now},
            "$push": {"assignment_history": history_entry}
        })
        await db.events.insert_one({
            "id": str(uuid.uuid4()),
            "type": "lead.assignment_rejected",
            "entity_type": "lead",
            "entity_id": lead_id,
            "data": {"user": user.get("email"), "reason": req.reason},
            "created_at": now
        })
    else:
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return {"data": lead}

@api_router.post("/leads/{lead_id}/transition")
async def transition_lead_stage(lead_id: str, request: Request):
    """Controlled stage transition with logging"""
    user = await get_current_user(request, db)
    body = await request.json()
    new_stage = body.get("stage")
    reason = body.get("reason", "")
    now = datetime.now(timezone.utc).isoformat()
    
    valid_stages = ["acquisition", "nurturing", "appointment", "booking", "recycle"]
    if new_stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {valid_stages}")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    old_stage = lead.get("stage", "acquisition")
    if old_stage == new_stage:
        return {"data": lead, "message": "Already in this stage"}
    
    # Update stage and compute response time if first contact
    update_fields = {"stage": new_stage, "updated_at": now}
    
    # If moving from acquisition to nurturing, track first contact time
    if old_stage == "acquisition" and new_stage == "nurturing":
        update_fields["status"] = "contacted"
        update_fields["last_contacted_at"] = now
        update_fields["follow_up_count"] = (lead.get("follow_up_count") or 0) + 1
        # Compute response time
        created_at = lead.get("created_at")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                now_dt = datetime.now(timezone.utc)
                response_minutes = int((now_dt - created_dt).total_seconds() / 60)
                update_fields["response_time_minutes"] = response_minutes
            except Exception:
                pass
    
    # Map stage to compatible status for backward compatibility
    stage_to_status = {"acquisition": "new", "nurturing": "contacted", "appointment": "prospect", "booking": "prospect", "recycle": "no_response"}
    if not body.get("keep_status"):
        update_fields["status"] = stage_to_status.get(new_stage, lead.get("status"))
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_fields})
    
    # Log event
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "lead.stage_changed",
        "entity_type": "lead",
        "entity_id": lead_id,
        "data": {"from_stage": old_stage, "to_stage": new_stage, "reason": reason, "by": user.get("email")},
        "created_at": now
    })
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return {"data": lead}

@api_router.get("/leads/{lead_id}/timeline")
async def get_lead_timeline(lead_id: str, request: Request):
    """Get comprehensive timeline for a lead (activities + events + assignments)"""
    user = await get_current_user(request, db)
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Gather all timeline items
    activities = await db.lead_activities.find({"lead_id": lead_id}, {"_id": 0}).to_list(100)
    events = await db.events.find({"entity_id": lead_id}, {"_id": 0}).to_list(100)
    wa_messages = await db.whatsapp_messages.find({"recipient_phone": lead.get("phone")}, {"_id": 0}).to_list(50)
    
    timeline = []
    for a in activities:
        timeline.append({"type": "activity", "subtype": a.get("type"), "description": a.get("description"), "outcome": a.get("outcome"), "created_by": a.get("created_by"), "created_at": a.get("created_at"), "id": a.get("id")})
    for e in events:
        timeline.append({"type": "event", "subtype": e.get("type"), "description": str(e.get("data", {})), "created_at": e.get("created_at"), "id": e.get("id")})
    for m in wa_messages:
        timeline.append({"type": "whatsapp", "subtype": m.get("message_type", "message"), "description": m.get("message", "")[:100], "status": m.get("status"), "created_by": m.get("sent_by"), "created_at": m.get("created_at"), "id": m.get("id")})
    
    # Add assignment history from lead doc
    for ah in (lead.get("assignment_history") or []):
        timeline.append({"type": "assignment", "subtype": ah.get("action"), "description": f"{ah.get('action','assigned')}: {ah.get('from', '?')} → {ah.get('to', '?')}", "reason": ah.get("reason"), "created_by": ah.get("assigned_by"), "created_at": ah.get("timestamp"), "id": None})
    
    # Sort by created_at descending
    timeline.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    
    return {"data": timeline}

# ==================== APPOINTMENT ROUTES ====================

@api_router.get("/appointments")
async def list_appointments(request: Request, status: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if status:
        query["status"] = status
    appointments = await db.appointments.find(query, {"_id": 0}).sort("scheduled_at", -1).to_list(100)
    return {"data": appointments}

@api_router.post("/appointments")
async def create_appointment(req: AppointmentCreate, request: Request):
    user = await get_current_user(request, db)
    appt_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": req.lead_id,
        "project_id": req.project_id,
        "scheduled_at": req.scheduled_at,
        "location": req.location,
        "notes": req.notes,
        "assigned_to": req.assigned_to or user.get("email"),
        "status": "pending",
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.appointments.insert_one(appt_doc)
    appt_doc.pop("_id", None)
    return {"data": appt_doc}

@api_router.put("/appointments/{appt_id}")
async def update_appointment(appt_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("id", None)
    body.pop("_id", None)
    await db.appointments.update_one({"id": appt_id}, {"$set": body})
    appt = await db.appointments.find_one({"id": appt_id}, {"_id": 0})
    return {"data": appt}

# ==================== DEAL ROUTES ====================

@api_router.get("/deals")
async def list_deals(
    request: Request,
    status: Optional[str] = None,
    project_id: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    user = await get_current_user(request, db)
    query = {}
    if status:
        query["status"] = status
    if project_id:
        query["project_id"] = project_id
    if search:
        query["$or"] = [
            {"customer_name": {"$regex": search, "$options": "i"}},
            {"customer_phone": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.deals.count_documents(query)
    deals = await db.deals.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"data": deals, "total": total}

@api_router.post("/deals")
async def create_deal(req: DealCreate, request: Request):
    user = await get_current_user(request, db)
    
    # Check unit availability
    unit = await db.units.find_one({"id": req.unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    if unit.get("status") not in ["available", None]:
        raise HTTPException(status_code=400, detail=f"Unit is not available (current: {unit.get('status')})")
    
    deal_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": req.lead_id,
        "customer_name": req.customer_name,
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "unit_id": req.unit_id,
        "unit_label": unit.get("label", ""),
        "project_id": req.project_id,
        "price": req.price,
        "payment_method": req.payment_method,
        "notes": req.notes,
        "status": "draft",
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.deals.insert_one(deal_doc)
    deal_doc.pop("_id", None)
    
    # Log event
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "deal.created",
        "entity_type": "deal",
        "entity_id": deal_doc["id"],
        "data": {"customer": req.customer_name, "unit": unit.get("label")},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"data": deal_doc}

@api_router.put("/deals/{deal_id}")
async def update_deal(deal_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("id", None)
    body.pop("_id", None)
    
    old_deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if not old_deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    await db.deals.update_one({"id": deal_id}, {"$set": body})
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    
    # Update unit status based on deal status
    new_status = body.get("status")
    if new_status and new_status != old_deal.get("status"):
        unit_status_map = {
            "reserved": "reserved",
            "booked": "booked",
            "active": "sold",
            "completed": "sold",
            "canceled": "available",
            "expired": "available",
            "failed": "available"
        }
        if new_status in unit_status_map:
            await db.units.update_one(
                {"id": old_deal["unit_id"]},
                {"$set": {"status": unit_status_map[new_status], "deal_status": new_status}}
            )
        
        await db.events.insert_one({
            "id": str(uuid.uuid4()),
            "type": f"deal.{new_status}",
            "entity_type": "deal",
            "entity_id": deal_id,
            "data": {"from": old_deal.get("status"), "to": new_status},
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"data": deal}

@api_router.post("/deals/{deal_id}/reserve")
async def reserve_deal(deal_id: str, request: Request):
    user = await get_current_user(request, db)
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal["status"] != "draft":
        raise HTTPException(status_code=400, detail="Can only reserve from draft status")
    
    await db.deals.update_one({"id": deal_id}, {"$set": {"status": "reserved", "reserved_at": datetime.now(timezone.utc).isoformat()}})
    await db.units.update_one({"id": deal["unit_id"]}, {"$set": {"status": "reserved", "deal_status": "reserved"}})
    
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    return {"data": deal}

@api_router.post("/deals/{deal_id}/booking")
async def book_deal(deal_id: str, request: Request):
    user = await get_current_user(request, db)
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal["status"] not in ["draft", "reserved"]:
        raise HTTPException(status_code=400, detail="Can only book from draft or reserved status")
    
    await db.deals.update_one({"id": deal_id}, {"$set": {"status": "booked", "booked_at": datetime.now(timezone.utc).isoformat()}})
    await db.units.update_one({"id": deal["unit_id"]}, {"$set": {"status": "booked", "deal_status": "booked"}})
    
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    return {"data": deal}

# ==================== WHATSAPP ROUTES ====================

@api_router.get("/whatsapp/messages")
async def list_whatsapp_messages(request: Request, skip: int = 0, limit: int = 50):
    user = await get_current_user(request, db)
    total = await db.whatsapp_messages.count_documents({})
    messages = await db.whatsapp_messages.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"data": messages, "total": total}

@api_router.post("/whatsapp/send")
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

@api_router.get("/whatsapp/templates")
async def list_whatsapp_templates(request: Request):
    user = await get_current_user(request, db)
    templates = await db.whatsapp_templates.find({}, {"_id": 0}).to_list(50)
    return {"data": templates}

# ==================== DEVELOPMENT REPORT ROUTES ====================

@api_router.get("/dev-report")
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

@api_router.post("/dev-report/items")
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

@api_router.put("/dev-report/items/{item_id}")
async def update_dev_report_item(item_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body.pop("id", None)
    body.pop("_id", None)
    await db.dev_report_items.update_one({"id": item_id}, {"$set": body})
    item = await db.dev_report_items.find_one({"id": item_id}, {"_id": 0})
    return {"data": item}

@api_router.delete("/dev-report/items/{item_id}")
async def delete_dev_report_item(item_id: str, request: Request):
    user = await get_current_user(request, db)
    await db.dev_report_items.delete_one({"id": item_id})
    return {"message": "Item deleted"}

@api_router.put("/dev-report/meta")
async def update_dev_report_meta(request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body["type"] = "meta"
    body["updated_by"] = user.get("email")
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.dev_report_meta.update_one({"type": "meta"}, {"$set": body}, upsert=True)
    return {"data": body}

# ==================== SITEPLAN ROUTES ====================

@api_router.get("/siteplan/{project_id}")
async def get_siteplan(project_id: str, request: Request, view_mode: str = "sales"):
    user = await get_current_user(request, db)
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    units = await db.units.find({"project_id": project_id}, {"_id": 0}).to_list(500)
    nodes = await db.siteplan_nodes.find({"project_id": project_id}, {"_id": 0}).to_list(500)
    
    # If no custom nodes, generate from units
    if not nodes:
        nodes = []
        for i, unit in enumerate(units):
            coords = unit.get("coordinates", {})
            nodes.append({
                "id": unit["id"],
                "unit_id": unit["id"],
                "label": unit.get("label", f"{unit.get('block','')}-{unit.get('number','')}"),
                "x": coords.get("x", (i % 8) * 80 + 30),
                "y": coords.get("y", (i // 8) * 60 + 30),
                "width": 65,
                "height": 45,
                "shape": "rect",
                "status": unit.get("status", "available"),
                "deal_status": unit.get("deal_status"),
                "construction_status": unit.get("construction_status", "not_started"),
                "payment_status": unit.get("payment_status"),
                "unit_type": unit.get("unit_type"),
                "price": unit.get("price", 0),
                "block": unit.get("block", ""),
                "number": unit.get("number", "")
            })
    
    # Color mappings per view mode
    color_maps = {
        "sales": {
            "available": "#94a3b8", "reserved": "#fbbf24", "booked": "#f97316",
            "sold": "#22c55e", "canceled": "#ef4444"
        },
        "construction": {
            "not_started": "#94a3b8", "in_progress": "#3b82f6", "qc_hold": "#f97316",
            "completed": "#22c55e", "delayed": "#ef4444"
        },
        "finance": {
            "unpaid": "#94a3b8", "dp_paid": "#3b82f6", "installment": "#fbbf24",
            "overdue": "#ef4444", "paid_off": "#22c55e"
        },
        "management": {
            "available": "#94a3b8", "reserved": "#fbbf24", "booked": "#f97316",
            "sold": "#22c55e", "canceled": "#ef4444"
        }
    }
    
    return {
        "data": {
            "project": project,
            "nodes": nodes,
            "view_mode": view_mode,
            "color_map": color_maps.get(view_mode, color_maps["sales"]),
            "summary": {
                "total": len(units),
                "available": sum(1 for u in units if u.get("status") == "available"),
                "reserved": sum(1 for u in units if u.get("status") == "reserved"),
                "booked": sum(1 for u in units if u.get("status") == "booked"),
                "sold": sum(1 for u in units if u.get("status") == "sold")
            }
        }
    }

# ==================== FINANCE ROUTES ====================

@api_router.get("/finance/billing")
async def list_billing_schedules(request: Request, deal_id: Optional[str] = None, project_id: Optional[str] = None, status: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if deal_id: query["deal_id"] = deal_id
    if project_id: query["project_id"] = project_id
    if status: query["items.status"] = status
    schedules = await db.billing_schedules.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"data": schedules}

@api_router.post("/finance/billing")
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

@api_router.post("/finance/payments")
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

@api_router.get("/finance/payments")
async def list_payments(request: Request, deal_id: Optional[str] = None, skip: int = 0, limit: int = 100):
    user = await get_current_user(request, db)
    query = {}
    if deal_id: query["deal_id"] = deal_id
    payments = await db.payments.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.payments.count_documents(query)
    return {"data": payments, "total": total}

@api_router.get("/finance/summary")
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

# ==================== CONSTRUCTION ROUTES ====================

@api_router.get("/construction/units")
async def list_construction_units(request: Request, project_id: Optional[str] = None, status: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if project_id: query["project_id"] = project_id
    if status: query["overall_status"] = status
    units = await db.construction_units.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"data": units}

@api_router.post("/construction/units")
async def create_construction_unit(request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    unit_id = body.get("unit_id")
    project_id = body.get("project_id")
    
    unit = await db.units.find_one({"id": unit_id}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    existing = await db.construction_units.find_one({"unit_id": unit_id})
    if existing:
        raise HTTPException(status_code=400, detail="Construction record already exists for this unit")
    
    # Default phases
    default_phases = [
        {"id": str(uuid.uuid4()), "name": "Pondasi / Foundation", "weight": 20, "status": "not_started", "progress": 0,
         "tasks": [
            {"id": str(uuid.uuid4()), "name": "Galian tanah", "weight": 30, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Pemasangan besi", "weight": 35, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Pengecoran", "weight": 35, "status": "not_started"},
         ]},
        {"id": str(uuid.uuid4()), "name": "Struktur / Structure", "weight": 25, "status": "not_started", "progress": 0,
         "tasks": [
            {"id": str(uuid.uuid4()), "name": "Kolom & balok", "weight": 40, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Dinding bata", "weight": 30, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Plat lantai", "weight": 30, "status": "not_started"},
         ]},
        {"id": str(uuid.uuid4()), "name": "Atap / Roofing", "weight": 15, "status": "not_started", "progress": 0,
         "tasks": [
            {"id": str(uuid.uuid4()), "name": "Rangka atap", "weight": 50, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Penutup atap", "weight": 50, "status": "not_started"},
         ]},
        {"id": str(uuid.uuid4()), "name": "Finishing", "weight": 25, "status": "not_started", "progress": 0,
         "tasks": [
            {"id": str(uuid.uuid4()), "name": "Plester & aci", "weight": 25, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Keramik & lantai", "weight": 25, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Cat", "weight": 25, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Sanitasi & plumbing", "weight": 25, "status": "not_started"},
         ]},
        {"id": str(uuid.uuid4()), "name": "MEP & Elektrikal", "weight": 15, "status": "not_started", "progress": 0,
         "tasks": [
            {"id": str(uuid.uuid4()), "name": "Instalasi listrik", "weight": 50, "status": "not_started"},
            {"id": str(uuid.uuid4()), "name": "Instalasi air", "weight": 50, "status": "not_started"},
         ]},
    ]
    
    construction_doc = {
        "id": str(uuid.uuid4()),
        "unit_id": unit_id,
        "project_id": project_id,
        "unit_label": unit.get("label", ""),
        "phases": default_phases,
        "overall_progress": 0,
        "overall_status": "not_started",
        "qc_results": [],
        "logs": [],
        "created_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.construction_units.insert_one(construction_doc)
    construction_doc.pop("_id", None)
    
    await db.units.update_one({"id": unit_id}, {"$set": {"construction_status": "not_started"}})
    return {"data": construction_doc}

@api_router.get("/construction/units/{unit_id}")
async def get_construction_unit(unit_id: str, request: Request):
    user = await get_current_user(request, db)
    cu = await db.construction_units.find_one({"unit_id": unit_id}, {"_id": 0})
    if not cu:
        raise HTTPException(status_code=404, detail="Construction record not found")
    return {"data": cu}

@api_router.put("/construction/units/{unit_id}/progress")
async def update_construction_progress(unit_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    phase_id = body.get("phase_id")
    task_id = body.get("task_id")
    new_status = body.get("status", "in_progress")
    notes = body.get("notes", "")
    
    cu = await db.construction_units.find_one({"unit_id": unit_id})
    if not cu:
        raise HTTPException(status_code=404, detail="Construction record not found")
    
    # Update specific task
    for phase in cu.get("phases", []):
        if phase["id"] == phase_id:
            if task_id:
                for task in phase.get("tasks", []):
                    if task["id"] == task_id:
                        task["status"] = new_status
                        break
            else:
                phase["status"] = new_status
            
            # Recalculate phase progress
            tasks = phase.get("tasks", [])
            if tasks:
                completed_weight = sum(t["weight"] for t in tasks if t["status"] in ["completed", "passed"])
                total_weight = sum(t["weight"] for t in tasks)
                phase["progress"] = round((completed_weight / total_weight * 100) if total_weight > 0 else 0)
                
                if all(t["status"] in ["completed", "passed"] for t in tasks):
                    phase["status"] = "completed"
                elif any(t["status"] == "failed" for t in tasks):
                    phase["status"] = "qc_hold"
                elif any(t["status"] in ["in_progress", "qc_pending"] for t in tasks):
                    phase["status"] = "in_progress"
    
    # Recalculate overall progress
    phases = cu.get("phases", [])
    overall = sum(p["progress"] * p["weight"] / 100 for p in phases) if phases else 0
    overall_status = "not_started"
    if overall >= 100:
        overall_status = "completed"
    elif overall > 0:
        overall_status = "in_progress"
    if any(p["status"] == "qc_hold" for p in phases):
        overall_status = "qc_hold"
    
    # Add log
    log_entry = {
        "id": str(uuid.uuid4()),
        "phase_id": phase_id,
        "task_id": task_id,
        "status": new_status,
        "notes": notes,
        "updated_by": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.construction_units.update_one(
        {"unit_id": unit_id},
        {"$set": {"phases": cu["phases"], "overall_progress": round(overall), "overall_status": overall_status, "updated_at": datetime.now(timezone.utc).isoformat()},
         "$push": {"logs": log_entry}}
    )
    
    # Sync to units collection
    await db.units.update_one({"id": unit_id}, {"$set": {"construction_status": overall_status, "construction_progress": round(overall)}})
    
    await db.events.insert_one({
        "id": str(uuid.uuid4()), "type": "construction.progress_updated",
        "entity_type": "construction", "entity_id": unit_id,
        "data": {"progress": round(overall), "status": overall_status, "notes": notes},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    updated = await db.construction_units.find_one({"unit_id": unit_id}, {"_id": 0})
    return {"data": updated}

@api_router.post("/construction/units/{unit_id}/qc")
async def submit_qc_result(unit_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    qc_doc = {
        "id": str(uuid.uuid4()),
        "phase_id": body.get("phase_id"),
        "task_id": body.get("task_id"),
        "result": body.get("result", "pass"),  # pass, fail
        "notes": body.get("notes", ""),
        "inspector": user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.construction_units.update_one({"unit_id": unit_id}, {"$push": {"qc_results": qc_doc}})
    
    # If QC failed, mark task as failed
    if qc_doc["result"] == "fail" and body.get("task_id"):
        cu = await db.construction_units.find_one({"unit_id": unit_id})
        for phase in cu.get("phases", []):
            if phase["id"] == body.get("phase_id"):
                for task in phase.get("tasks", []):
                    if task["id"] == body["task_id"]:
                        task["status"] = "failed"
                phase["status"] = "qc_hold"
        await db.construction_units.update_one({"unit_id": unit_id}, {"$set": {"phases": cu["phases"], "overall_status": "qc_hold"}})
        await db.units.update_one({"id": unit_id}, {"$set": {"construction_status": "qc_hold"}})
    
    await db.events.insert_one({
        "id": str(uuid.uuid4()), "type": f"qc.{'passed' if qc_doc['result'] == 'pass' else 'failed'}",
        "entity_type": "qc", "entity_id": qc_doc["id"],
        "data": {"unit_id": unit_id, "result": qc_doc["result"]},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"data": qc_doc}

@api_router.get("/construction/summary")
async def construction_summary(request: Request, project_id: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if project_id: query["project_id"] = project_id
    all_cu = await db.construction_units.find(query, {"_id": 0}).to_list(500)
    
    total = len(all_cu)
    not_started = sum(1 for c in all_cu if c["overall_status"] == "not_started")
    in_progress = sum(1 for c in all_cu if c["overall_status"] == "in_progress")
    completed = sum(1 for c in all_cu if c["overall_status"] == "completed")
    qc_hold = sum(1 for c in all_cu if c["overall_status"] == "qc_hold")
    avg_progress = round(sum(c.get("overall_progress", 0) for c in all_cu) / max(total, 1))
    
    return {"data": {
        "total": total, "not_started": not_started, "in_progress": in_progress,
        "completed": completed, "qc_hold": qc_hold, "avg_progress": avg_progress
    }}

# ==================== NOTIFICATION CENTER ROUTES ====================

@api_router.get("/notifications")
async def list_notifications(request: Request, unread_only: bool = False, skip: int = 0, limit: int = 50):
    user = await get_current_user(request, db)
    query = {"$or": [{"target_user": user.get("email")}, {"target_user": None}, {"target_user": "all"}]}
    if unread_only:
        query["read"] = False
    total = await db.notifications.count_documents(query)
    notifs = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    unread = await db.notifications.count_documents({**query, "read": False})
    return {"data": notifs, "total": total, "unread": unread}

@api_router.post("/notifications")
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

@api_router.put("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, request: Request):
    user = await get_current_user(request, db)
    await db.notifications.update_one({"id": notif_id}, {"$set": {"read": True}})
    return {"message": "Marked as read"}

@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(request: Request):
    user = await get_current_user(request, db)
    query = {"$or": [{"target_user": user.get("email")}, {"target_user": None}, {"target_user": "all"}]}
    await db.notifications.update_many(query, {"$set": {"read": True}})
    return {"message": "All marked as read"}

# ---- Auto Follow-Up Rules ----
@api_router.get("/notifications/auto-rules")
async def list_auto_followup_rules(request: Request):
    user = await get_current_user(request, db)
    rules = await db.auto_followup_rules.find({}, {"_id": 0}).to_list(50)
    return {"data": rules}

@api_router.post("/notifications/auto-rules")
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

@api_router.put("/notifications/auto-rules/{rule_id}")
async def update_auto_followup_rule(rule_id: str, request: Request):
    user = await get_current_user(request, db)
    body = await request.json()
    body.pop("id", None)
    body.pop("_id", None)
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.auto_followup_rules.update_one({"id": rule_id}, {"$set": body})
    rule = await db.auto_followup_rules.find_one({"id": rule_id}, {"_id": 0})
    return {"data": rule}

@api_router.delete("/notifications/auto-rules/{rule_id}")
async def delete_auto_followup_rule(rule_id: str, request: Request):
    user = await get_current_user(request, db)
    await db.auto_followup_rules.delete_one({"id": rule_id})
    return {"message": "Rule deleted"}

@api_router.post("/notifications/simulate-followup")
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

# ==================== APPOINTMENT CALENDAR ROUTES ====================

@api_router.get("/appointments/calendar")
async def get_appointment_calendar(request: Request, month: Optional[str] = None, project_id: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if project_id:
        query["project_id"] = project_id
    if month:
        query["scheduled_at"] = {"$regex": f"^{month}"}
    appointments = await db.appointments.find(query, {"_id": 0}).sort("scheduled_at", 1).to_list(200)
    
    # Enrich with lead names
    for appt in appointments:
        if appt.get("lead_id"):
            lead = await db.leads.find_one({"id": appt["lead_id"]}, {"_id": 0, "name": 1, "phone": 1})
            if lead:
                appt["lead_name"] = lead.get("name")
                appt["lead_phone"] = lead.get("phone")
    
    return {"data": appointments}

# ==================== DASHBOARD ROUTES ====================

@api_router.get("/dashboard")
async def get_dashboard(request: Request):
    user = await get_current_user(request, db)
    
    # Projects summary
    total_projects = await db.projects.count_documents({})
    active_projects = await db.projects.count_documents({"status": {"$in": ["active", "planning", "construction"]}})
    
    # Units summary
    total_units = await db.units.count_documents({})
    available_units = await db.units.count_documents({"status": "available"})
    reserved_units = await db.units.count_documents({"status": "reserved"})
    booked_units = await db.units.count_documents({"status": "booked"})
    sold_units = await db.units.count_documents({"status": "sold"})
    
    # Leads summary
    total_leads = await db.leads.count_documents({})
    new_leads = await db.leads.count_documents({"status": "new"})
    contacted_leads = await db.leads.count_documents({"status": "contacted"})
    prospect_leads = await db.leads.count_documents({"status": "prospect"})
    
    # Deals summary
    total_deals = await db.deals.count_documents({})
    active_deals = await db.deals.count_documents({"status": {"$in": ["draft", "reserved", "booked", "active"]}})
    
    # Revenue
    pipeline = [{"$match": {"status": {"$in": ["booked", "active", "completed"]}}}, {"$group": {"_id": None, "total": {"$sum": "$price"}}}]
    revenue_result = await db.deals.aggregate(pipeline).to_list(1)
    total_revenue = revenue_result[0]["total"] if revenue_result else 0
    
    # Recent activities
    recent_events = await db.events.find({}, {"_id": 0}).sort("created_at", -1).to_list(10)
    
    # Lead sources
    lead_source_pipeline = [{"$group": {"_id": "$source", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    lead_sources = await db.leads.aggregate(lead_source_pipeline).to_list(20)
    
    # Finance summary
    fin_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_amount"}, "paid": {"$sum": "$paid_amount"}, "outstanding": {"$sum": "$outstanding"}}}]
    fin_agg = await db.billing_schedules.aggregate(fin_pipeline).to_list(1)
    fin_data = fin_agg[0] if fin_agg else {"total": 0, "paid": 0, "outstanding": 0}
    
    # Construction summary
    total_construction = await db.construction_units.count_documents({})
    construction_completed = await db.construction_units.count_documents({"overall_status": "completed"})
    construction_in_progress = await db.construction_units.count_documents({"overall_status": "in_progress"})
    
    # Unread notifications
    notif_query = {"$or": [{"target_user": user.get("email")}, {"target_user": None}, {"target_user": "all"}], "read": False}
    unread_notifs = await db.notifications.count_documents(notif_query)
    
    # Upcoming appointments
    upcoming_appts = await db.appointments.find({"status": {"$in": ["pending", "confirmed"]}}, {"_id": 0}).sort("scheduled_at", 1).to_list(5)
    for appt in upcoming_appts:
        if appt.get("lead_id"):
            lead = await db.leads.find_one({"id": appt["lead_id"]}, {"_id": 0, "name": 1, "phone": 1})
            if lead:
                appt["lead_name"] = lead.get("name")
                appt["lead_phone"] = lead.get("phone")
    
    # User-specific metrics for role-based dashboards
    user_email = user.get("email")
    user_role = user.get("role", "sales")
    my_leads = await db.leads.count_documents({"assigned_to": user_email, "stage": {"$nin": ["recycle"]}})
    my_leads_acquisition = await db.leads.count_documents({"assigned_to": user_email, "stage": "acquisition"})
    my_leads_nurturing = await db.leads.count_documents({"assigned_to": user_email, "stage": "nurturing"})
    my_leads_appointment = await db.leads.count_documents({"assigned_to": user_email, "stage": "appointment"})
    my_appointments = await db.appointments.count_documents({"assigned_to": user_email, "status": {"$in": ["pending", "confirmed"]}})
    
    # Stage counts (primary lifecycle metric)
    stage_counts = {
        "acquisition": await db.leads.count_documents({"stage": "acquisition"}),
        "nurturing": await db.leads.count_documents({"stage": "nurturing"}),
        "appointment": await db.leads.count_documents({"stage": "appointment"}),
        "booking": await db.leads.count_documents({"stage": "booking"}),
        "recycle": await db.leads.count_documents({"stage": "recycle"}),
    }
    
    # Unassigned leads (for marketing admin to distribute)
    unassigned_leads = await db.leads.count_documents({"$or": [{"assigned_to": None}, {"assigned_to": ""}], "stage": {"$nin": ["recycle"]}})
    
    result = {
        "data": {
            "projects": {"total": total_projects, "active": active_projects},
            "units": {"total": total_units, "available": available_units, "reserved": reserved_units, "booked": booked_units, "sold": sold_units},
            "leads": {"total": total_leads, "new": new_leads, "contacted": contacted_leads, "prospect": prospect_leads},
            "deals": {"total": total_deals, "active": active_deals},
            "revenue": {"total": total_revenue},
            "finance": {"total_billing": fin_data["total"], "paid": fin_data["paid"], "outstanding": fin_data["outstanding"]},
            "construction": {"total": total_construction, "completed": construction_completed, "in_progress": construction_in_progress},
            "notifications": {"unread": unread_notifs},
            "upcoming_appointments": upcoming_appts,
            "recent_events": recent_events,
            "lead_sources": [{"source": s["_id"] or "unknown", "count": s["count"]} for s in lead_sources],
            "lead_stages": stage_counts,
            "leads_not_contacted": await db.leads.count_documents({"stage": "acquisition", "follow_up_count": {"$in": [0, None]}}),
            "leads_assigned_to_user": my_leads,
            "unassigned_leads": unassigned_leads,
            "my_leads": {
                "total": my_leads,
                "acquisition": my_leads_acquisition,
                "nurturing": my_leads_nurturing,
                "appointment": my_leads_appointment,
            },
            "my_appointments": my_appointments,
            "user_role": user_role,
            "user_email": user_email,
            "overdue_payments": await db.billing_schedules.count_documents({"outstanding": {"$gt": 0}}),
            "pending_assignments": await db.leads.count_documents({"assigned_to": user_email, "assignment_status": "pending"}),
        }
    }
    
    # Compute response time stats inline
    rt_pipeline = [
        {"$match": {"response_time_minutes": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": None, "avg": {"$avg": "$response_time_minutes"}, "count": {"$sum": 1}}}
    ]
    rt_stats = await db.leads.aggregate(rt_pipeline).to_list(1)
    if rt_stats:
        result["data"]["avg_response_minutes"] = round(rt_stats[0]["avg"])
        result["data"]["responded_leads"] = rt_stats[0]["count"]
    else:
        result["data"]["avg_response_minutes"] = 0
        result["data"]["responded_leads"] = 0
    
    return result

# ==================== SEED DATA ====================

async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@sipro.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hashed,
            "name": "Admin SIPRO",
            "role": "super_admin",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"Admin user seeded: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
        logger.info(f"Admin password updated: {admin_email}")

async def seed_sample_data():
    """Seed sample data for demo purposes"""
    # Check if already seeded
    existing_projects = await db.projects.count_documents({})
    if existing_projects > 0:
        return
    
    # Create sample organization
    org_doc = {
        "id": "org-001",
        "name": "PT Sipro Development",
        "type": "developer",
        "address": "Jakarta, Indonesia",
        "phone": "+62-21-12345678",
        "email": "info@sipro-dev.com",
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.organizations.insert_one(org_doc)
    
    # Create sample projects
    projects = [
        {"id": "proj-001", "name": "Grand Permata Residence", "location": "Tangerang Selatan", "description": "Perumahan premium dengan konsep modern minimalis", "total_units": 50, "target_revenue": 75000000000, "status": "active", "units_sold": 15, "units_available": 30, "units_reserved": 5, "revenue_realized": 22500000000},
        {"id": "proj-002", "name": "Bukit Harmoni Village", "location": "Bogor", "description": "Hunian asri di kaki gunung dengan harga terjangkau", "total_units": 100, "target_revenue": 50000000000, "status": "active", "units_sold": 30, "units_available": 60, "units_reserved": 10, "revenue_realized": 15000000000},
        {"id": "proj-003", "name": "Riverside Park City", "location": "Bekasi", "description": "Kota mandiri dengan fasilitas lengkap di tepi sungai", "total_units": 200, "target_revenue": 200000000000, "status": "planning", "units_sold": 0, "units_available": 200, "units_reserved": 0, "revenue_realized": 0},
    ]
    for p in projects:
        p["organization_id"] = "org-001"
        p["created_by"] = "admin@sipro.com"
        p["created_at"] = datetime.now(timezone.utc).isoformat()
        p["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.projects.insert_many(projects)
    
    # Generate units for project 1
    statuses = ["available"] * 30 + ["reserved"] * 5 + ["sold"] * 15
    blocks = ["A", "B", "C"]
    unit_types = ["Type 36/72", "Type 45/90", "Type 60/120"]
    prices = [500000000, 750000000, 1200000000]
    
    units = []
    idx = 0
    for b_idx, block in enumerate(blocks):
        count = [15, 20, 15][b_idx]
        for i in range(1, count + 1):
            status = statuses[idx] if idx < len(statuses) else "available"
            units.append({
                "id": f"unit-{block}-{i}",
                "project_id": "proj-001",
                "block": block,
                "number": str(i),
                "label": f"{block}-{i}",
                "unit_type": unit_types[b_idx],
                "floor_area": [36, 45, 60][b_idx],
                "land_area": [72, 90, 120][b_idx],
                "price": prices[b_idx],
                "status": status,
                "deal_status": "active" if status == "sold" else ("reserved" if status == "reserved" else None),
                "construction_status": ["not_started", "in_progress", "completed"][idx % 3] if status == "sold" else "not_started",
                "payment_status": "paid" if status == "sold" else None,
                "coordinates": {"x": ((i-1) % 5) * 80 + 30, "y": ((i-1) // 5) * 60 + 30 + b_idx * 200},
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            idx += 1
    await db.units.insert_many(units)
    
    # Generate units for project 2
    units2 = []
    for block in ["D", "E", "F", "G"]:
        for i in range(1, 26):
            status = "available" if (i + ord(block)) % 4 != 0 else ("sold" if (i + ord(block)) % 3 == 0 else "reserved")
            units2.append({
                "id": f"unit-{block}-{i}",
                "project_id": "proj-002",
                "block": block,
                "number": str(i),
                "label": f"{block}-{i}",
                "unit_type": "Type 36/72",
                "floor_area": 36,
                "land_area": 72,
                "price": 350000000,
                "status": status,
                "deal_status": "active" if status == "sold" else ("reserved" if status == "reserved" else None),
                "construction_status": "not_started",
                "payment_status": None,
                "coordinates": {"x": ((i-1) % 5) * 80 + 30, "y": ((i-1) // 5) * 60 + 30},
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    await db.units.insert_many(units2)
    
    # Sample leads
    lead_sources = ["meta_ads", "google_ads", "tiktok_ads", "referral", "walk_in", "website", "event"]
    lead_statuses = ["new", "contacted", "prospect", "no_response", "lost"]
    sample_leads = []
    names = ["Budi Santoso", "Siti Rahayu", "Ahmad Hidayat", "Dewi Lestari", "Rudi Hartono", "Rina Susanti",
             "Agus Pratama", "Nisa Fitriani", "Hendra Wijaya", "Putri Ayu", "Dedi Kurniawan", "Lina Mariani",
             "Joko Widodo", "Maya Sari", "Bambang Sugiarto", "Ratna Dewi", "Eko Prasetyo", "Wulan Sari",
             "Yusuf Maulana", "Indah Permata"]
    
    # Map status to stage for seed consistency
    status_to_stage_map = {"new": "acquisition", "contacted": "nurturing", "prospect": "appointment", "no_response": "recycle", "lost": "recycle"}
    
    for i, name in enumerate(names):
        status = lead_statuses[i % len(lead_statuses)]
        sample_leads.append({
            "id": f"lead-{i+1:03d}",
            "name": name,
            "phone": f"+6281{2000000+i}",
            "email": f"{name.lower().replace(' ', '.')}@email.com",
            "source": lead_sources[i % len(lead_sources)],
            "campaign": f"Campaign Q1 2026" if i % 2 == 0 else "Campaign Q4 2025",
            "ad_set": f"Ad Set {chr(65 + i % 5)}",
            "ad_name": f"Ad Creative {i % 3 + 1}",
            "notes": "",
            "project_id": "proj-001" if i < 12 else "proj-002",
            "assigned_to": "admin@sipro.com",
            "status": status,
            "stage": status_to_stage_map.get(status, "acquisition"),
            "quality_score": (i * 17 + 30) % 100,
            "follow_up_count": 1 if status in ("contacted", "prospect") else 0,
            "last_contacted_at": datetime.now(timezone.utc).isoformat() if status in ("contacted", "prospect") else None,
            "nurturing_outcome": None,
            "created_by": "admin@sipro.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    await db.leads.insert_many(sample_leads)
    
    # Sample deals
    sample_deals = []
    for i in range(8):
        deal_statuses = ["draft", "reserved", "booked", "active", "completed", "active", "booked", "reserved"]
        sample_deals.append({
            "id": f"deal-{i+1:03d}",
            "lead_id": f"lead-{i+1:03d}",
            "customer_name": names[i],
            "customer_email": f"{names[i].lower().replace(' ', '.')}@email.com",
            "customer_phone": f"+6281{2000000+i}",
            "unit_id": f"unit-{'ABC'[i%3]}-{i+1}",
            "unit_label": f"{'ABC'[i%3]}-{i+1}",
            "project_id": "proj-001",
            "price": prices[i % 3],
            "payment_method": ["cash", "kpr", "installment", "cash"][i % 4],
            "notes": "",
            "status": deal_statuses[i],
            "created_by": "admin@sipro.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    await db.deals.insert_many(sample_deals)
    
    # Sample WhatsApp messages
    wa_messages = [
        {"recipient_phone": "+62812000001", "recipient_name": "Budi Santoso", "message": "Halo Pak Budi, terima kasih telah mengunjungi Grand Permata Residence. Apakah Bapak tertarik untuk survey?", "message_type": "follow_up", "status": "sent"},
        {"recipient_phone": "+62812000002", "recipient_name": "Siti Rahayu", "message": "Reminder: Appointment survey Anda di Grand Permata Residence hari Sabtu jam 10:00", "message_type": "reminder", "status": "sent"},
        {"recipient_phone": "+62812000003", "recipient_name": "Ahmad Hidayat", "message": "Selamat! Booking fee Anda untuk unit A-3 telah diterima.", "message_type": "notification", "status": "sent"},
    ]
    for msg in wa_messages:
        msg["id"] = str(uuid.uuid4())
        msg["sent_by"] = "admin@sipro.com"
        msg["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.whatsapp_messages.insert_many(wa_messages)
    
    # Sample dev report items
    dev_items = [
        {"module": "Authentication", "feature": "Login & Register", "status": "completed", "priority": "high"},
        {"module": "Authentication", "feature": "Role-Based Access Control", "status": "completed", "priority": "high"},
        {"module": "Organization", "feature": "Organization Management", "status": "completed", "priority": "high"},
        {"module": "Project", "feature": "Project CRUD", "status": "completed", "priority": "high"},
        {"module": "Project", "feature": "Unit Generation", "status": "completed", "priority": "high"},
        {"module": "Siteplan", "feature": "Interactive Siteplan", "status": "completed", "priority": "high"},
        {"module": "CRM", "feature": "Lead Management", "status": "completed", "priority": "high"},
        {"module": "CRM", "feature": "Lead Import from Ads", "status": "completed", "priority": "high"},
        {"module": "Deal", "feature": "Deal Lifecycle", "status": "completed", "priority": "high"},
        {"module": "WhatsApp", "feature": "Message Sending Hooks", "status": "completed", "priority": "medium"},
        {"module": "Dashboard", "feature": "Main Dashboard", "status": "completed", "priority": "high"},
        {"module": "Dev Report", "feature": "Development Report Module", "status": "completed", "priority": "medium"},
        {"module": "Finance", "feature": "Billing & Payment", "status": "not_started", "priority": "high", "milestone": "Phase 3"},
        {"module": "Finance", "feature": "Collection Management", "status": "not_started", "priority": "high", "milestone": "Phase 3"},
        {"module": "Finance", "feature": "Commission Engine", "status": "not_started", "priority": "medium", "milestone": "Phase 3"},
        {"module": "Construction", "feature": "Progress Tracking", "status": "not_started", "priority": "high", "milestone": "Phase 4"},
        {"module": "Construction", "feature": "QC Management", "status": "not_started", "priority": "medium", "milestone": "Phase 4"},
        {"module": "Document", "feature": "Document Workflow", "status": "not_started", "priority": "high", "milestone": "Phase 5"},
        {"module": "Accounting", "feature": "Journal & Ledger", "status": "not_started", "priority": "medium", "milestone": "Phase 6"},
        {"module": "Portal", "feature": "Customer Portal", "status": "not_started", "priority": "medium", "milestone": "Phase 5"},
        {"module": "Workflow", "feature": "Automation Engine", "status": "not_started", "priority": "low", "milestone": "Phase 6"},
        {"module": "Reporting", "feature": "Analytics Dashboard", "status": "not_started", "priority": "medium", "milestone": "Phase 6"},
    ]
    for item in dev_items:
        item["id"] = str(uuid.uuid4())
        item["notes"] = item.get("notes", "")
        item["milestone"] = item.get("milestone", "Phase 1")
        item["blockers"] = item.get("blockers", "")
        item["created_by"] = "admin@sipro.com"
        item["created_at"] = datetime.now(timezone.utc).isoformat()
        item["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.dev_report_items.insert_many(dev_items)
    
    # WhatsApp templates
    wa_templates = [
        {"id": str(uuid.uuid4()), "name": "Follow Up Survey", "message": "Halo {name}, terima kasih telah menghubungi kami. Apakah Anda tertarik untuk melakukan survey ke {project}?", "type": "follow_up"},
        {"id": str(uuid.uuid4()), "name": "Appointment Reminder", "message": "Reminder: Appointment survey Anda di {project} pada {date} jam {time}. Sampai jumpa!", "type": "reminder"},
        {"id": str(uuid.uuid4()), "name": "Booking Confirmation", "message": "Selamat {name}! Booking fee Anda untuk unit {unit} di {project} telah diterima. Tim kami akan menghubungi Anda.", "type": "notification"},
        {"id": str(uuid.uuid4()), "name": "Payment Reminder", "message": "Halo {name}, ini pengingat pembayaran untuk unit {unit}. Jatuh tempo: {due_date}. Silakan hubungi finance kami.", "type": "payment_reminder"},
    ]
    await db.whatsapp_templates.insert_many(wa_templates)
    
    # Sample billing schedules for deals
    billing_schedules = []
    for i in range(4):
        deal = sample_deals[i]
        total_price = deal["price"]
        items = [
            {"id": str(uuid.uuid4()), "description": "Booking Fee", "amount": total_price * 0.05, "due_date": "2026-02-01", "status": "paid", "paid_amount": total_price * 0.05},
            {"id": str(uuid.uuid4()), "description": "Down Payment 1", "amount": total_price * 0.15, "due_date": "2026-03-01", "status": "paid" if i < 2 else "pending", "paid_amount": total_price * 0.15 if i < 2 else 0},
            {"id": str(uuid.uuid4()), "description": "Down Payment 2", "amount": total_price * 0.10, "due_date": "2026-04-01", "status": "pending", "paid_amount": 0},
            {"id": str(uuid.uuid4()), "description": "Angsuran 1", "amount": total_price * 0.10, "due_date": "2026-05-01", "status": "pending", "paid_amount": 0},
            {"id": str(uuid.uuid4()), "description": "Angsuran 2", "amount": total_price * 0.10, "due_date": "2026-06-01", "status": "pending", "paid_amount": 0},
            {"id": str(uuid.uuid4()), "description": "Pelunasan", "amount": total_price * 0.50, "due_date": "2026-12-01", "status": "pending", "paid_amount": 0},
        ]
        paid_total = sum(it["paid_amount"] for it in items)
        billing_schedules.append({
            "id": f"bill-{i+1:03d}",
            "deal_id": deal["id"],
            "unit_id": deal["unit_id"],
            "project_id": deal["project_id"],
            "customer_name": deal["customer_name"],
            "items": items,
            "total_amount": total_price,
            "paid_amount": paid_total,
            "outstanding": total_price - paid_total,
            "status": "active",
            "created_by": "admin@sipro.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    await db.billing_schedules.insert_many(billing_schedules)
    
    # Sample payments
    sample_payments = []
    for i, bs in enumerate(billing_schedules):
        for item in bs["items"]:
            if item["status"] == "paid":
                sample_payments.append({
                    "id": str(uuid.uuid4()),
                    "deal_id": bs["deal_id"],
                    "billing_item_id": item["id"],
                    "amount": item["amount"],
                    "payment_date": item["due_date"],
                    "payment_method": "transfer",
                    "reference": f"TRF-{uuid.uuid4().hex[:8].upper()}",
                    "notes": "",
                    "status": "confirmed",
                    "recorded_by": "admin@sipro.com",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
    if sample_payments:
        await db.payments.insert_many(sample_payments)
    
    # Sample construction units
    construction_units = []
    for i in range(6):
        unit_id = f"unit-A-{i+1}"
        progress_levels = [85, 60, 40, 20, 10, 0]
        statuses_map = ["in_progress", "in_progress", "in_progress", "in_progress", "in_progress", "not_started"]
        phases = [
            {"id": str(uuid.uuid4()), "name": "Pondasi / Foundation", "weight": 20, "status": "completed" if progress_levels[i] > 20 else "in_progress" if progress_levels[i] > 0 else "not_started", "progress": min(100, progress_levels[i] * 5),
             "tasks": [
                {"id": str(uuid.uuid4()), "name": "Galian tanah", "weight": 30, "status": "completed" if progress_levels[i] > 5 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Pemasangan besi", "weight": 35, "status": "completed" if progress_levels[i] > 10 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Pengecoran", "weight": 35, "status": "completed" if progress_levels[i] > 15 else "not_started"},
             ]},
            {"id": str(uuid.uuid4()), "name": "Struktur / Structure", "weight": 25, "status": "completed" if progress_levels[i] > 45 else "in_progress" if progress_levels[i] > 20 else "not_started", "progress": max(0, min(100, (progress_levels[i] - 20) * 4)),
             "tasks": [
                {"id": str(uuid.uuid4()), "name": "Kolom & balok", "weight": 40, "status": "completed" if progress_levels[i] > 30 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Dinding bata", "weight": 30, "status": "completed" if progress_levels[i] > 38 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Plat lantai", "weight": 30, "status": "completed" if progress_levels[i] > 45 else "not_started"},
             ]},
            {"id": str(uuid.uuid4()), "name": "Atap / Roofing", "weight": 15, "status": "completed" if progress_levels[i] > 60 else "in_progress" if progress_levels[i] > 45 else "not_started", "progress": max(0, min(100, (progress_levels[i] - 45) * 6)),
             "tasks": [
                {"id": str(uuid.uuid4()), "name": "Rangka atap", "weight": 50, "status": "completed" if progress_levels[i] > 52 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Penutup atap", "weight": 50, "status": "completed" if progress_levels[i] > 60 else "not_started"},
             ]},
            {"id": str(uuid.uuid4()), "name": "Finishing", "weight": 25, "status": "in_progress" if progress_levels[i] > 60 else "not_started", "progress": max(0, min(100, (progress_levels[i] - 60) * 4)),
             "tasks": [
                {"id": str(uuid.uuid4()), "name": "Plester & aci", "weight": 25, "status": "completed" if progress_levels[i] > 70 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Keramik & lantai", "weight": 25, "status": "completed" if progress_levels[i] > 75 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Cat", "weight": 25, "status": "in_progress" if progress_levels[i] > 78 else "not_started"},
                {"id": str(uuid.uuid4()), "name": "Sanitasi & plumbing", "weight": 25, "status": "not_started"},
             ]},
            {"id": str(uuid.uuid4()), "name": "MEP & Elektrikal", "weight": 15, "status": "not_started", "progress": 0,
             "tasks": [
                {"id": str(uuid.uuid4()), "name": "Instalasi listrik", "weight": 50, "status": "not_started"},
                {"id": str(uuid.uuid4()), "name": "Instalasi air", "weight": 50, "status": "not_started"},
             ]},
        ]
        construction_units.append({
            "id": str(uuid.uuid4()),
            "unit_id": unit_id,
            "project_id": "proj-001",
            "unit_label": f"A-{i+1}",
            "phases": phases,
            "overall_progress": progress_levels[i],
            "overall_status": statuses_map[i],
            "qc_results": [],
            "logs": [],
            "created_by": "admin@sipro.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
    await db.construction_units.insert_many(construction_units)
    
    # Sample notifications
    sample_notifs = [
        {"title": "Lead Baru dari Meta Ads", "message": "Budi Santoso baru saja mengisi form dari kampanye Meta Ads. Follow up segera!", "type": "follow_up", "target_user": "admin@sipro.com", "related_entity_type": "lead", "related_entity_id": "lead-001"},
        {"title": "Pembayaran Diterima", "message": "Pembayaran booking fee dari Siti Rahayu untuk unit A-2 telah dikonfirmasi.", "type": "success", "target_user": "admin@sipro.com"},
        {"title": "Jadwal Survey Hari Ini", "message": "Ada 3 jadwal survey hari ini. Pastikan tim sales siap.", "type": "info", "target_user": "all"},
        {"title": "Progress Konstruksi Unit A-1", "message": "Unit A-1 telah mencapai 85% progress. Tahap finishing sedang berlangsung.", "type": "info", "target_user": "admin@sipro.com"},
        {"title": "Overdue Payment Alert", "message": "Down Payment 2 untuk deal Ahmad Hidayat sudah melewati jatuh tempo.", "type": "danger", "target_user": "admin@sipro.com"},
    ]
    for n in sample_notifs:
        n["id"] = str(uuid.uuid4())
        n["read"] = False
        n["created_by"] = "system"
        n["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.notifications.insert_many(sample_notifs)
    
    # Auto follow-up rules
    auto_rules = [
        {
            "id": str(uuid.uuid4()), "name": "Auto WA untuk Lead Baru dari Ads",
            "trigger_event": "lead.created",
            "delay_minutes": 5,
            "message_template": "Halo {name}! Terima kasih telah tertarik dengan proyek kami. Tim sales kami akan segera menghubungi Anda. Ada yang bisa kami bantu?",
            "channel": "whatsapp", "is_active": True, "executions": 12,
            "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()), "name": "Reminder Follow-up 24 Jam",
            "trigger_event": "lead.created",
            "delay_minutes": 1440,
            "message_template": "Halo {name}, apakah Anda masih tertarik untuk mengetahui lebih lanjut tentang proyek kami? Kami dengan senang hati bisa menjadwalkan survey untuk Anda.",
            "channel": "whatsapp", "is_active": True, "executions": 8,
            "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()), "name": "Notifikasi Internal Lead Baru",
            "trigger_event": "lead.created",
            "delay_minutes": 0,
            "message_template": "Lead baru masuk: {name} dari {source}. Segera follow up!",
            "channel": "in_app", "is_active": True, "executions": 20,
            "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat()
        },
    ]
    await db.auto_followup_rules.insert_many(auto_rules)
    
    # Sample appointments
    sample_appts = [
        {"id": str(uuid.uuid4()), "lead_id": "lead-001", "project_id": "proj-001", "scheduled_at": "2026-04-07T10:00:00", "location": "Grand Permata Residence Marketing Gallery", "notes": "Survey rumah Type 45", "assigned_to": "admin@sipro.com", "status": "confirmed", "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "lead_id": "lead-003", "project_id": "proj-001", "scheduled_at": "2026-04-07T14:00:00", "location": "Grand Permata Residence Marketing Gallery", "notes": "Follow-up pembayaran", "assigned_to": "admin@sipro.com", "status": "pending", "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "lead_id": "lead-005", "project_id": "proj-002", "scheduled_at": "2026-04-08T09:00:00", "location": "Bukit Harmoni Village Site Office", "notes": "Survey pertama", "assigned_to": "admin@sipro.com", "status": "pending", "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "lead_id": "lead-007", "project_id": "proj-001", "scheduled_at": "2026-04-09T11:00:00", "location": "Grand Permata Residence", "notes": "", "assigned_to": "admin@sipro.com", "status": "confirmed", "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat()},
    ]
    await db.appointments.insert_many(sample_appts)
    
    # Update dev report items - mark new ones as completed/in_progress
    await db.dev_report_items.update_many(
        {"module": "Finance", "feature": "Billing & Payment"},
        {"$set": {"status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await db.dev_report_items.update_many(
        {"module": "Finance", "feature": "Collection Management"},
        {"$set": {"status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await db.dev_report_items.update_many(
        {"module": "Construction", "feature": "Progress Tracking"},
        {"$set": {"status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    await db.dev_report_items.update_many(
        {"module": "Construction", "feature": "QC Management"},
        {"$set": {"status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    # Add new items for notification center
    new_dev_items = [
        {"id": str(uuid.uuid4()), "module": "Notification", "feature": "Real-time Notification Center", "status": "completed", "priority": "high", "milestone": "Phase 2", "notes": "", "blockers": "", "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "module": "Notification", "feature": "Auto Follow-Up Engine", "status": "completed", "priority": "high", "milestone": "Phase 2", "notes": "Auto WA for new leads from ads", "blockers": "", "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(uuid.uuid4()), "module": "CRM", "feature": "Appointment Calendar", "status": "completed", "priority": "medium", "milestone": "Phase 2", "notes": "", "blockers": "", "created_by": "admin@sipro.com", "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()},
    ]
    await db.dev_report_items.insert_many(new_dev_items)
    
    logger.info("Sample data seeded successfully")

async def create_indexes():
    await db.users.create_index("email", unique=True)
    await db.leads.create_index("phone")
    await db.leads.create_index("email")
    await db.leads.create_index("status")
    await db.leads.create_index("stage")
    await db.leads.create_index("assigned_to")
    await db.leads.create_index("source")
    await db.leads.create_index("project_id")
    await db.units.create_index("project_id")
    await db.units.create_index("status")
    await db.deals.create_index("project_id")
    await db.deals.create_index("status")
    await db.deals.create_index("unit_id")
    await db.events.create_index([("created_at", -1)])
    await db.login_attempts.create_index("identifier")
    await db.billing_schedules.create_index("deal_id")
    await db.payments.create_index("deal_id")
    await db.construction_units.create_index("unit_id")
    await db.construction_units.create_index("project_id")
    await db.notifications.create_index([("created_at", -1)])
    await db.notifications.create_index("target_user")
    await db.appointments.create_index("scheduled_at")

async def migrate_lead_stages():
    """Non-destructive migration: populate stage for leads that don't have it"""
    status_to_stage_map = {"new": "acquisition", "contacted": "nurturing", "prospect": "appointment", "no_response": "recycle", "lost": "recycle"}
    
    leads_without_stage = await db.leads.count_documents({"$or": [{"stage": {"$exists": False}}, {"stage": None}]})
    if leads_without_stage == 0:
        return
    
    logger.info(f"Migrating {leads_without_stage} leads to add stage field")
    
    for status_val, stage_val in status_to_stage_map.items():
        result = await db.leads.update_many(
            {"status": status_val, "$or": [{"stage": {"$exists": False}}, {"stage": None}]},
            {"$set": {"stage": stage_val, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        if result.modified_count > 0:
            logger.info(f"  Migrated {result.modified_count} leads: status={status_val} -> stage={stage_val}")
    
    # Default any remaining without stage to acquisition
    result = await db.leads.update_many(
        {"$or": [{"stage": {"$exists": False}}, {"stage": None}]},
        {"$set": {"stage": "acquisition", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.modified_count > 0:
        logger.info(f"  Migrated {result.modified_count} remaining leads to stage=acquisition")
    
    # Also ensure follow_up_count and other fields exist
    await db.leads.update_many(
        {"follow_up_count": {"$exists": False}},
        {"$set": {"follow_up_count": 0}}
    )
    await db.leads.update_many(
        {"last_contacted_at": {"$exists": False}},
        {"$set": {"last_contacted_at": None}}
    )
    await db.leads.update_many(
        {"nurturing_outcome": {"$exists": False}},
        {"$set": {"nurturing_outcome": None}}
    )

# ==================== APP SETUP ====================

@app.on_event("startup")
async def startup():
    await create_indexes()
    await seed_admin()
    await seed_sample_data()
    await migrate_lead_stages()
    
    # Write test credentials
    creds_dir = Path("/app/memory")
    creds_dir.mkdir(exist_ok=True)
    creds_file = creds_dir / "test_credentials.md"
    creds_file.write_text(
        "# SIPRO Test Credentials\n\n"
        f"## Admin\n- Email: {os.environ.get('ADMIN_EMAIL', 'admin@sipro.com')}\n"
        f"- Password: {os.environ.get('ADMIN_PASSWORD', 'admin123')}\n"
        f"- Role: super_admin\n\n"
        "## Auth Endpoints\n"
        "- POST /api/auth/login\n"
        "- POST /api/auth/register\n"
        "- POST /api/auth/logout\n"
        "- GET /api/auth/me\n"
        "- POST /api/auth/refresh\n"
    )
    logger.info("SIPRO startup complete")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.environ.get("FRONTEND_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "https://erp-sipro-rebuild.preview.emergentagent.com",
        "https://sipro-dev-env.preview.emergentagent.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
