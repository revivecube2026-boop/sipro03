"""Extracted router for siteplan (Phase F refactor)."""
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

# ==================== SITEPLAN ROUTES ====================

@router.get("/siteplan/{project_id}")
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

