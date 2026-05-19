"""Extracted router for construction (Phase F refactor)."""
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

# ==================== CONSTRUCTION ROUTES ====================

@router.get("/construction/units")
async def list_construction_units(request: Request, project_id: Optional[str] = None, status: Optional[str] = None):
    user = await get_current_user(request, db)
    query = {}
    if project_id: query["project_id"] = project_id
    if status: query["overall_status"] = status
    units = await db.construction_units.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"data": units}

@router.post("/construction/units")
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

@router.get("/construction/units/{unit_id}")
async def get_construction_unit(unit_id: str, request: Request):
    user = await get_current_user(request, db)
    cu = await db.construction_units.find_one({"unit_id": unit_id}, {"_id": 0})
    if not cu:
        raise HTTPException(status_code=404, detail="Construction record not found")
    return {"data": cu}

@router.put("/construction/units/{unit_id}/progress")
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

@router.post("/construction/units/{unit_id}/qc")
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

@router.get("/construction/summary")
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

