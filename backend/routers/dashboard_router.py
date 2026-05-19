"""Extracted router for dashboard (Phase F refactor)."""
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

# ==================== DASHBOARD ROUTES ====================

@router.get("/dashboard")
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
            "my_tasks": {
                "open": await db.tasks.count_documents({"assigned_to": user_email, "status": {"$in": ["open", "in_progress", "snoozed"]}}),
                "overdue": await db.tasks.count_documents({"assigned_to": user_email, "status": {"$in": ["open", "in_progress", "snoozed"]}, "due_date": {"$lt": datetime.now(timezone.utc).isoformat()}}),
                "completed": await db.tasks.count_documents({"assigned_to": user_email, "status": "completed"}),
            },
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

