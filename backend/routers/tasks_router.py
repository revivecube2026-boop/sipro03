"""Phase C — Task Engine routes."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Request, HTTPException

from deps import db, get_current_user
from shared import _apply_task_scope, _get_task_permissions
from models import TaskCreate, TaskUpdate, TaskComplete, TaskPermissionsUpdate

router = APIRouter()


@router.get("/tasks")
async def list_tasks(
    request: Request,
    status: Optional[str] = None,
    type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    mine: Optional[bool] = False,
    overdue: Optional[bool] = False,
    skip: int = 0,
    limit: int = 100,
):
    user = await get_current_user(request, db)
    query: dict = {}
    if status:
        query["status"] = {"$in": status.split(",")} if "," in status else status
    if type:
        query["type"] = type
    if assigned_to:
        query["assigned_to"] = assigned_to
    if mine:
        query["assigned_to"] = user.get("email")
    if related_entity_type:
        query["related_entity_type"] = related_entity_type
    if related_entity_id:
        query["related_entity_id"] = related_entity_id
    if overdue:
        query["due_date"] = {"$lt": datetime.now(timezone.utc).isoformat()}
        query["status"] = {"$in": ["open", "in_progress", "snoozed"]}
    query = _apply_task_scope(user, query)
    total = await db.tasks.count_documents(query)
    tasks = await db.tasks.find(query, {"_id": 0}).sort("due_date", 1).skip(skip).limit(limit).to_list(limit)
    lead_ids = [t["related_entity_id"] for t in tasks if t.get("related_entity_type") == "lead" and t.get("related_entity_id")]
    if lead_ids:
        leads = await db.leads.find({"id": {"$in": list(set(lead_ids))}}, {"_id": 0, "id": 1, "name": 1, "phone": 1, "stage": 1}).to_list(len(lead_ids))
        lead_map = {l["id"]: l for l in leads}
        for t in tasks:
            if t.get("related_entity_type") == "lead":
                lead = lead_map.get(t.get("related_entity_id"))
                if lead:
                    t["related_lead_name"] = lead.get("name")
                    t["related_lead_phone"] = lead.get("phone")
                    t["related_lead_stage"] = lead.get("stage")
    return {"data": tasks, "total": total}


@router.get("/tasks/stats")
async def tasks_stats(request: Request, mine: Optional[bool] = False):
    user = await get_current_user(request, db)
    base: dict = {}
    if mine:
        base["assigned_to"] = user.get("email")
    now_iso = datetime.now(timezone.utc).isoformat()
    open_q = {**base, "status": {"$in": ["open", "in_progress", "snoozed"]}}
    overdue_q = {**open_q, "due_date": {"$lt": now_iso}}
    today_end = (datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)).isoformat()
    today_q = {**open_q, "due_date": {"$lte": today_end, "$gte": now_iso}}
    return {
        "data": {
            "total_open": await db.tasks.count_documents(open_q),
            "overdue": await db.tasks.count_documents(overdue_q),
            "today": await db.tasks.count_documents(today_q),
            "completed": await db.tasks.count_documents({**base, "status": "completed"}),
            "by_type": {
                t: await db.tasks.count_documents({**open_q, "type": t})
                for t in ["follow_up", "appointment", "contact", "recycle", "custom"]
            },
        }
    }


@router.get("/tasks/permissions")
async def get_tasks_permissions(request: Request):
    await get_current_user(request, db)
    return {"data": {"allowed_roles": await _get_task_permissions()}}


@router.put("/tasks/permissions")
async def update_tasks_permissions(req: TaskPermissionsUpdate, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "marketing_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can change task permissions")
    now = datetime.now(timezone.utc).isoformat()
    await db.app_settings.update_one(
        {"key": "tasks_permissions"},
        {"$set": {"key": "tasks_permissions", "allowed_roles": req.allowed_roles, "updated_at": now, "updated_by": user.get("email")}},
        upsert=True,
    )
    return {"data": {"allowed_roles": req.allowed_roles}}


@router.post("/tasks")
async def create_task(req: TaskCreate, request: Request):
    user = await get_current_user(request, db)
    allowed = await _get_task_permissions()
    if user.get("role") not in allowed and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Your role is not allowed to create tasks")
    now = datetime.now(timezone.utc).isoformat()
    task_doc = {
        "id": str(uuid.uuid4()),
        "title": req.title,
        "description": req.description,
        "type": req.type,
        "status": "open",
        "priority": req.priority,
        "related_entity_type": req.related_entity_type,
        "related_entity_id": req.related_entity_id,
        "assigned_to": req.assigned_to or user.get("email"),
        "due_date": req.due_date,
        "source_event": f"manual:{uuid.uuid4()}",
        "auto_generated": False,
        "outcome": None,
        "activity_history": [{"action": "created", "by": user.get("email"), "at": now}],
        "created_by": user.get("email"),
        "created_at": now,
        "updated_at": now,
    }
    await db.tasks.insert_one(task_doc)
    task_doc.pop("_id", None)
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "task.created",
        "entity_type": "task",
        "entity_id": task_doc["id"],
        "data": {"title": req.title, "type": req.type, "related": req.related_entity_id},
        "created_at": now,
    })
    return {"data": task_doc}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    await get_current_user(request, db)
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"data": task}


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, req: TaskUpdate, request: Request):
    user = await get_current_user(request, db)
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    now = datetime.now(timezone.utc).isoformat()
    update_fields = {k: v for k, v in req.dict().items() if v is not None}
    update_fields["updated_at"] = now
    history_entry = {"action": "updated", "by": user.get("email"), "at": now, "changes": {k: v for k, v in update_fields.items() if k != "updated_at"}}
    await db.tasks.update_one({"id": task_id}, {"$set": update_fields, "$push": {"activity_history": history_entry}})
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return {"data": task}


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, req: TaskComplete, request: Request):
    user = await get_current_user(request, db)
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    now = datetime.now(timezone.utc).isoformat()
    history_entry = {"action": "completed", "by": user.get("email"), "at": now, "outcome": req.outcome}
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {"status": "completed", "outcome": req.outcome, "completed_at": now, "updated_at": now}, "$push": {"activity_history": history_entry}},
    )
    await db.events.insert_one({
        "id": str(uuid.uuid4()),
        "type": "task.completed",
        "entity_type": "task",
        "entity_id": task_id,
        "data": {"outcome": req.outcome, "by": user.get("email")},
        "created_at": now,
    })
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return {"data": task}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    user = await get_current_user(request, db)
    if user.get("role") not in ["super_admin", "marketing_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can delete tasks")
    await db.tasks.delete_one({"id": task_id})
    return {"message": "Task deleted"}
