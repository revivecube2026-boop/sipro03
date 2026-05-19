"""Phase C - Task Engine backend tests.

Covers:
- /api/tasks CRUD + filters
- /api/tasks/stats
- /api/tasks/permissions GET/PUT
- /api/tasks/{id}/complete
- Auto-tasks on lead.created, lead.transition (nurturing/appointment/booking/recycle)
- Auto-task on appointment.created (reminder)
- Idempotency via source_event dedup
- Dashboard my_tasks counts
"""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sipro-tasks.preview.emergentagent.com").rstrip("/")


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed {email}: {r.text}"
    return r.json().get("token")


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@sipro.com", "admin123")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {admin_token}"})
    return s


# ---------- Tasks permissions ----------
class TestTaskPermissions:
    def test_get_permissions_default(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/tasks/permissions")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "allowed_roles" in data
        assert isinstance(data["allowed_roles"], list)

    def test_update_permissions_persists(self, admin_client):
        new_roles = ["super_admin", "marketing_admin", "sales"]
        r = admin_client.put(f"{BASE_URL}/api/tasks/permissions", json={"allowed_roles": new_roles})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["allowed_roles"] == new_roles
        # verify GET
        r2 = admin_client.get(f"{BASE_URL}/api/tasks/permissions")
        assert sorted(r2.json()["data"]["allowed_roles"]) == sorted(new_roles)
        # restore defaults
        admin_client.put(
            f"{BASE_URL}/api/tasks/permissions",
            json={"allowed_roles": ["super_admin", "marketing_admin", "marketing_inhouse", "sales"]},
        )


# ---------- Tasks CRUD ----------
class TestTasksCRUD:
    def test_create_manual_task(self, admin_client):
        payload = {
            "title": "TEST_manual_task",
            "description": "manual",
            "type": "custom",
            "priority": "medium",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        r = admin_client.post(f"{BASE_URL}/api/tasks", json=payload)
        assert r.status_code == 200, r.text
        t = r.json()["data"]
        assert t["title"] == payload["title"]
        assert t["type"] == "custom"
        assert t["status"] == "open"
        assert t["auto_generated"] is False
        assert t["created_by"] == "admin@sipro.com"
        assert "id" in t
        pytest.task_id = t["id"]

        # GET verify
        r2 = admin_client.get(f"{BASE_URL}/api/tasks/{t['id']}")
        assert r2.status_code == 200
        assert r2.json()["data"]["title"] == payload["title"]

    def test_list_tasks(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/tasks")
        assert r.status_code == 200
        data = r.json()
        assert "data" in data and isinstance(data["data"], list)
        assert data["total"] >= 1

    def test_filter_status(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/tasks", params={"status": "open"})
        assert r.status_code == 200
        for t in r.json()["data"]:
            assert t["status"] == "open"

    def test_filter_mine(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/tasks", params={"mine": "true"})
        assert r.status_code == 200
        for t in r.json()["data"]:
            assert t.get("assigned_to") == "admin@sipro.com"

    def test_update_task(self, admin_client):
        tid = getattr(pytest, "task_id", None)
        assert tid
        r = admin_client.put(f"{BASE_URL}/api/tasks/{tid}", json={"priority": "high", "status": "in_progress"})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["priority"] == "high"
        assert d["status"] == "in_progress"
        # activity_history appended
        assert any(h.get("action") == "updated" for h in d.get("activity_history", []))

    def test_complete_task(self, admin_client):
        tid = getattr(pytest, "task_id", None)
        assert tid
        r = admin_client.post(f"{BASE_URL}/api/tasks/{tid}/complete", json={"outcome": "TEST_done"})
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["status"] == "completed"
        assert d["outcome"] == "TEST_done"
        assert d.get("completed_at")

    def test_stats(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/tasks/stats")
        assert r.status_code == 200
        s = r.json()["data"]
        for k in ["total_open", "overdue", "today", "completed", "by_type"]:
            assert k in s
        assert isinstance(s["by_type"], dict)

    def test_delete_admin(self, admin_client):
        # create then delete
        r = admin_client.post(f"{BASE_URL}/api/tasks", json={"title": "TEST_to_del", "type": "custom"})
        tid = r.json()["data"]["id"]
        d = admin_client.delete(f"{BASE_URL}/api/tasks/{tid}")
        assert d.status_code == 200, d.text
        # verify gone
        g = admin_client.get(f"{BASE_URL}/api/tasks/{tid}")
        assert g.status_code == 404


# ---------- Auto-tasks on Lead lifecycle ----------
class TestAutoTasksLead:
    @pytest.fixture(scope="class")
    def created_lead(self, admin_client):
        payload = {
            "name": f"TEST_AutoTaskLead_{uuid.uuid4().hex[:6]}",
            "phone": "+62" + str(int(time.time()))[-9:],
            "source": "website",
        }
        r = admin_client.post(f"{BASE_URL}/api/leads", json=payload)
        assert r.status_code == 200, r.text
        return r.json()["data"]

    def test_lead_created_contact_task(self, admin_client, created_lead):
        lid = created_lead["id"]
        # poll briefly
        for _ in range(5):
            r = admin_client.get(
                f"{BASE_URL}/api/tasks",
                params={"related_entity_type": "lead", "related_entity_id": lid, "type": "contact"},
            )
            tasks = r.json()["data"]
            if tasks:
                break
            time.sleep(0.3)
        assert tasks, "No contact task auto-created for new lead"
        t = tasks[0]
        assert t["type"] == "contact"
        assert t["priority"] == "high"
        assert t["auto_generated"] is True
        assert t["status"] == "open"
        assert created_lead["name"] in t["title"]
        assert t["source_event"] == f"lead.created:{lid}"

    def test_transition_nurturing(self, admin_client, created_lead):
        lid = created_lead["id"]
        r = admin_client.post(f"{BASE_URL}/api/leads/{lid}/transition", json={"stage": "nurturing"})
        assert r.status_code == 200, r.text
        r2 = admin_client.get(
            f"{BASE_URL}/api/tasks",
            params={"related_entity_id": lid, "type": "follow_up"},
        )
        tasks = [t for t in r2.json()["data"] if t["source_event"] == f"lead.stage:nurturing:{lid}"]
        assert tasks, "follow_up task not created on nurturing"
        assert tasks[0]["type"] == "follow_up"

    def test_transition_appointment(self, admin_client, created_lead):
        lid = created_lead["id"]
        r = admin_client.post(f"{BASE_URL}/api/leads/{lid}/transition", json={"stage": "appointment"})
        assert r.status_code == 200, r.text
        r2 = admin_client.get(
            f"{BASE_URL}/api/tasks", params={"related_entity_id": lid, "type": "appointment"}
        )
        tasks = [t for t in r2.json()["data"] if t["source_event"] == f"lead.stage:appointment:{lid}"]
        assert tasks, "appointment task not created"
        assert tasks[0]["priority"] == "high"

    def test_transition_booking(self, admin_client, created_lead):
        lid = created_lead["id"]
        r = admin_client.post(f"{BASE_URL}/api/leads/{lid}/transition", json={"stage": "booking"})
        assert r.status_code == 200, r.text
        r2 = admin_client.get(f"{BASE_URL}/api/tasks", params={"related_entity_id": lid})
        tasks = [t for t in r2.json()["data"] if t["source_event"] == f"lead.stage:booking:{lid}"]
        assert tasks, "booking task not created"

    def test_transition_recycle(self, admin_client, created_lead):
        lid = created_lead["id"]
        r = admin_client.post(f"{BASE_URL}/api/leads/{lid}/transition", json={"stage": "recycle"})
        assert r.status_code == 200, r.text
        r2 = admin_client.get(f"{BASE_URL}/api/tasks", params={"related_entity_id": lid, "type": "recycle"})
        tasks = [t for t in r2.json()["data"] if t["source_event"] == f"lead.stage:recycle:{lid}"]
        assert tasks, "recycle task not created"
        assert tasks[0]["priority"] == "low"

    def test_dedup_no_duplicate(self, admin_client, created_lead):
        """Re-trigger nurturing transition; should NOT create a 2nd open task for same source_event."""
        lid = created_lead["id"]
        # move back to acquisition first
        admin_client.post(f"{BASE_URL}/api/leads/{lid}/transition", json={"stage": "acquisition"})
        admin_client.post(f"{BASE_URL}/api/leads/{lid}/transition", json={"stage": "nurturing"})
        r = admin_client.get(f"{BASE_URL}/api/tasks", params={"related_entity_id": lid})
        nurturing_tasks = [t for t in r.json()["data"] if t["source_event"] == f"lead.stage:nurturing:{lid}"]
        open_count = sum(1 for t in nurturing_tasks if t["status"] in ["open", "in_progress", "snoozed"])
        assert open_count == 1, f"Expected 1 open nurturing task, got {open_count}"


# ---------- Auto-task on appointment ----------
class TestAutoTaskAppointment:
    def test_appointment_creates_reminder(self, admin_client):
        # Create a lead first
        lead_r = admin_client.post(
            f"{BASE_URL}/api/leads",
            json={"name": "TEST_ApptLead", "phone": "+628" + str(int(time.time()))[-8:], "source": "referral"},
        )
        assert lead_r.status_code == 200
        lid = lead_r.json()["data"]["id"]
        sched = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        r = admin_client.post(
            f"{BASE_URL}/api/appointments",
            json={"lead_id": lid, "scheduled_at": sched, "location": "Office", "notes": "TEST"},
        )
        assert r.status_code == 200, r.text
        aid = r.json()["data"]["id"]
        r2 = admin_client.get(
            f"{BASE_URL}/api/tasks",
            params={"related_entity_type": "appointment", "related_entity_id": aid},
        )
        tasks = r2.json()["data"]
        assert tasks, "Reminder task not auto-created for appointment"
        t = tasks[0]
        assert t["type"] == "appointment"
        assert t["priority"] == "high"
        assert t["source_event"] == f"appointment.created:{aid}"


# ---------- Permission enforcement ----------
class TestPermissionEnforcement:
    def test_create_without_role(self, admin_client):
        # Set permissions to exclude 'sales'
        admin_client.put(
            f"{BASE_URL}/api/tasks/permissions",
            json={"allowed_roles": ["super_admin"]},
        )
        # Try to create as admin (super_admin) — should still pass
        r = admin_client.post(f"{BASE_URL}/api/tasks", json={"title": "TEST_perm", "type": "custom"})
        assert r.status_code == 200
        # Restore defaults
        admin_client.put(
            f"{BASE_URL}/api/tasks/permissions",
            json={"allowed_roles": ["super_admin", "marketing_admin", "marketing_inhouse", "sales"]},
        )


# ---------- Dashboard my_tasks ----------
class TestDashboardMyTasks:
    def test_dashboard_my_tasks(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "my_tasks" in data
        mt = data["my_tasks"]
        for k in ["open", "overdue", "completed"]:
            assert k in mt
            assert isinstance(mt[k], int)
