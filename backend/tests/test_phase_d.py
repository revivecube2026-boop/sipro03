"""Phase D Production Hardening Tests for SIPRO.

Tests:
- Phone normalization (create, import, dedup across formats)
- Idempotent response_time / first_contacted_at
- Strict RBAC (sales role) for leads, tasks, appointments, deals
- Admin & marketing_admin override (no scope)
- Auto-assign load balancing (returns `loads` dict)
- Atomic unit booking (concurrent POST /api/deals same unit → only one wins)
- reserved_until set on deals
- Expire-reservations endpoint (admin vs sales)
- MongoDB indexes existence
- Cookie security flags (COOKIE_SECURE=false in dev)
- first_contacted_at backfill on existing leads
"""
import os
import time
import uuid
import threading
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sipro-tasks.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# ---------- Helpers / Fixtures ----------

def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"No token for {email}: {data}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    s.last_login_response = r
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin@sipro.com", "admin123")


@pytest.fixture(scope="module")
def sales1():
    return _login("sales1@sipro.com", "sipro123")


@pytest.fixture(scope="module")
def sales2():
    return _login("sales2@sipro.com", "sipro123")


@pytest.fixture(scope="module")
def mktadmin():
    return _login("marketing_admin@sipro.com", "sipro123")


def _rand_phone_local():
    # 8xxxxxxxxx (10 digits after the leading 8) → +6281...
    return "081" + str(uuid.uuid4().int)[:9]


# ==================== PHONE NORMALIZATION ====================

class TestPhoneNormalization:
    def test_create_lead_with_local_phone_stored_as_e164(self, admin):
        local = _rand_phone_local()  # 0812...
        expected = "+62" + local[1:]
        payload = {"name": "TEST_phone_local", "phone": local, "source": "manual"}
        r = admin.post(f"{API}/leads", json=payload)
        assert r.status_code == 200, r.text
        data = r.json().get("data") or r.json()
        assert data.get("phone") == expected, f"Expected {expected}, got {data.get('phone')}"

        # GET to confirm persistence
        lead_id = data["id"]
        g = admin.get(f"{API}/leads/{lead_id}")
        assert g.status_code == 200
        assert (g.json().get("data") or {}).get("phone") == expected

    def test_dedup_across_phone_formats(self, admin):
        local = _rand_phone_local()
        e164 = "+62" + local[1:]
        # First create with local format
        r1 = admin.post(f"{API}/leads", json={"name": "TEST_dedup_a", "phone": local, "source": "manual"})
        assert r1.status_code == 200, r1.text
        # Second create with E.164 format must be rejected
        r2 = admin.post(f"{API}/leads", json={"name": "TEST_dedup_b", "phone": e164, "source": "manual"})
        assert r2.status_code == 400, f"Expected 400 on dup, got {r2.status_code}: {r2.text}"

    def test_import_normalizes_phone(self, admin):
        local = _rand_phone_local()
        expected = "+62" + local[1:]
        body = {
            "leads": [{"name": "TEST_import_phone", "phone": local, "source": "csv"}],
            "source": "csv_import",
            "campaign": "TEST_PhaseD",
        }
        r = admin.post(f"{API}/leads/import", json=body)
        assert r.status_code == 200, r.text
        # Lookup imported lead
        lst = admin.get(f"{API}/leads", params={"search": "TEST_import_phone", "limit": 50})
        items = (lst.json().get("data") or [])
        phones = [it.get("phone") for it in items if it.get("name") == "TEST_import_phone"]
        assert expected in phones, f"Expected {expected} in {phones}"


# ==================== IDEMPOTENT RESPONSE TIME ====================

class TestIdempotentResponseTime:
    def test_first_contacted_at_set_once(self, admin):
        # Create a lead in acquisition
        local = _rand_phone_local()
        r = admin.post(f"{API}/leads", json={"name": "TEST_idem_rt", "phone": local, "source": "manual"})
        assert r.status_code == 200, r.text
        lead_id = (r.json().get("data") or {}).get("id")
        assert lead_id

        # acquisition -> nurturing (first transition)
        t1 = admin.post(f"{API}/leads/{lead_id}/transition", json={"stage": "nurturing", "reason": "first"})
        assert t1.status_code == 200, t1.text
        d1 = admin.get(f"{API}/leads/{lead_id}").json().get("data") or {}
        fca1 = d1.get("first_contacted_at")
        rt1 = d1.get("response_time_minutes")
        assert fca1 is not None, "first_contacted_at not set after first nurturing transition"

        # nurturing -> acquisition (revert)
        t2 = admin.post(f"{API}/leads/{lead_id}/transition", json={"stage": "acquisition", "reason": "revert"})
        assert t2.status_code == 200, t2.text

        # Wait a tiny bit so any (wrong) recomputation would differ
        time.sleep(2)

        # acquisition -> nurturing (second transition)
        t3 = admin.post(f"{API}/leads/{lead_id}/transition", json={"stage": "nurturing", "reason": "second"})
        assert t3.status_code == 200, t3.text
        d3 = admin.get(f"{API}/leads/{lead_id}").json().get("data") or {}
        fca3 = d3.get("first_contacted_at")
        rt3 = d3.get("response_time_minutes")
        assert fca3 == fca1, f"first_contacted_at changed: {fca1} -> {fca3}"
        assert rt3 == rt1, f"response_time_minutes changed: {rt1} -> {rt3}"


# ==================== STRICT RBAC ====================

class TestRBAC:
    def test_sales1_sees_only_own_leads(self, sales1):
        r = sales1.get(f"{API}/leads", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        for it in items:
            assert it.get("assigned_to") == "sales1@sipro.com", \
                f"Sales1 saw lead assigned to {it.get('assigned_to')}"

    def test_sales1_cannot_get_unowned_lead(self, sales1, admin):
        # admin creates a lead assigned to admin (or unassigned to admin email)
        local = _rand_phone_local()
        c = admin.post(f"{API}/leads", json={
            "name": "TEST_rbac_admin_lead", "phone": local, "source": "manual",
            "assigned_to": "admin@sipro.com",
        })
        assert c.status_code == 200, c.text
        lead_id = (c.json().get("data") or {}).get("id")
        # sales1 should get 403
        r = sales1.get(f"{API}/leads/{lead_id}")
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"
        body = r.json()
        msg = body.get("detail") or body.get("message") or ""
        assert "milik" in str(msg).lower() or "bukan" in str(msg).lower(), f"Unexpected error message: {msg}"

    def test_sales1_tasks_scope(self, sales1):
        r = sales1.get(f"{API}/tasks", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        for t in items:
            assert t.get("assigned_to") == "sales1@sipro.com", \
                f"Sales1 saw task assigned to {t.get('assigned_to')}"

    def test_sales1_appointments_scope(self, sales1):
        r = sales1.get(f"{API}/appointments", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        for a in items:
            assert a.get("assigned_to") == "sales1@sipro.com", \
                f"Sales1 saw appointment assigned to {a.get('assigned_to')}"

    def test_sales1_deals_scope(self, sales1):
        r = sales1.get(f"{API}/deals", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        for d in items:
            assert d.get("created_by") == "sales1@sipro.com", \
                f"Sales1 saw deal created_by {d.get('created_by')}"

    def test_admin_no_scope_leads(self, admin):
        r = admin.get(f"{API}/leads", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        # Admin should see leads from various owners (or no items if DB empty)
        owners = {it.get("assigned_to") for it in items}
        # As long as it returns and doesn't filter strictly by admin email, it's fine
        # Verify by checking at least one non-admin assigned lead exists if items exist
        if len(items) >= 2:
            assert owners != {"admin@sipro.com"}, "Admin appears scoped to own leads only"

    def test_marketing_admin_no_scope(self, mktadmin, admin):
        # ensure there are leads assigned to others
        r = mktadmin.get(f"{API}/leads", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        # Compare count to admin's view — should be equal (both see everything)
        a = admin.get(f"{API}/leads", params={"limit": 500})
        a_total = a.json().get("total")
        m_total = r.json().get("total")
        assert a_total == m_total, f"marketing_admin total {m_total} != admin total {a_total}"


# ==================== AUTO-ASSIGN LOAD BALANCING ====================

class TestAutoAssign:
    def test_auto_assign_returns_loads_dict(self, admin):
        # Create 3 unassigned leads in acquisition
        created = []
        for i in range(3):
            local = _rand_phone_local()
            r = admin.post(f"{API}/leads", json={
                "name": f"TEST_auto_{i}", "phone": local, "source": "manual",
                # leave assigned_to unset → unassigned
            })
            assert r.status_code == 200, r.text
            created.append((r.json().get("data") or {}).get("id"))

        r = admin.post(f"{API}/leads/auto-assign", json={"stage": "acquisition"})
        assert r.status_code == 200, r.text
        data = r.json().get("data") or {}
        assert "loads" in data, f"Response missing 'loads': {data}"
        loads = data["loads"]
        assert isinstance(loads, dict) and len(loads) >= 1, f"loads not a non-empty dict: {loads}"
        # Each value should be int
        for k, v in loads.items():
            assert isinstance(v, int), f"load value for {k} not int: {v}"


# ==================== ATOMIC UNIT BOOKING ====================

class TestAtomicBooking:
    def _get_or_create_available_unit(self, admin):
        # Find any available unit
        r = admin.get(f"{API}/units", params={"status": "available", "limit": 5})
        if r.status_code == 200:
            items = r.json().get("data") or []
            if items:
                return items[0]
        # Create a project + unit
        projects = admin.get(f"{API}/projects", params={"limit": 1}).json().get("data") or []
        if not projects:
            cp = admin.post(f"{API}/projects", json={"name": "TEST_proj_phaseD", "location": "Jkt"})
            assert cp.status_code == 200, cp.text
            project_id = (cp.json().get("data") or {}).get("id")
        else:
            project_id = projects[0]["id"]
        cu = admin.post(f"{API}/units", json={
            "project_id": project_id, "label": f"TEST_U_{uuid.uuid4().hex[:6]}",
            "type": "house", "price": 500000000, "status": "available",
        })
        assert cu.status_code == 200, cu.text
        return cu.json().get("data") or {}

    def test_concurrent_deal_creation_only_one_wins(self, admin):
        unit = self._get_or_create_available_unit(admin)
        unit_id = unit.get("id")
        project_id = unit.get("project_id")
        assert unit_id and project_id

        results = []
        token = admin.headers.get("Authorization")

        def make_deal(i):
            sess = requests.Session()
            sess.headers.update({"Content-Type": "application/json", "Authorization": token})
            try:
                r = sess.post(f"{API}/deals", json={
                    "lead_id": None,
                    "customer_name": f"TEST_cc_{i}",
                    "customer_email": f"cc{i}@test.com",
                    "customer_phone": "08111000200",
                    "unit_id": unit_id,
                    "project_id": project_id,
                    "price": 500000000,
                    "payment_method": "cash",
                    "notes": "concurrent test",
                })
                results.append((i, r.status_code, r.text[:200]))
            except Exception as e:
                results.append((i, "ERR", str(e)))

        ts = [threading.Thread(target=make_deal, args=(i,)) for i in range(2)]
        for t in ts: t.start()
        for t in ts: t.join()

        statuses = [s for _, s, _ in results]
        ok = sum(1 for s in statuses if s == 200)
        bad = sum(1 for s in statuses if s == 400)
        assert ok == 1, f"Expected exactly 1 success, got statuses={statuses} bodies={results}"
        assert bad == 1, f"Expected exactly 1 conflict (400), got statuses={statuses} bodies={results}"

        # Verify unit moved to holding
        gu = admin.get(f"{API}/units/{unit_id}")
        if gu.status_code == 200:
            data = gu.json().get("data") or {}
            assert data.get("status") in ("holding", "reserved", "booked"), \
                f"Unit status after deal should be holding/reserved, got {data.get('status')}"


# ==================== reserved_until / expire-reservations ====================

class TestReservation:
    def test_deal_has_reserved_until(self, admin):
        # Need an available unit
        unit = TestAtomicBooking()._get_or_create_available_unit(admin)
        unit_id = unit.get("id")
        project_id = unit.get("project_id")
        r = admin.post(f"{API}/deals", json={
            "customer_name": "TEST_res_until",
            "customer_phone": "08110000111",
            "unit_id": unit_id,
            "project_id": project_id,
            "price": 100000000,
            "payment_method": "cash",
        })
        assert r.status_code == 200, r.text
        d = r.json().get("data") or {}
        assert d.get("reserved_until"), f"reserved_until missing: {d}"

    def test_expire_reservations_admin_ok(self, admin):
        r = admin.post(f"{API}/deals/expire-reservations", json={})
        assert r.status_code == 200, r.text
        data = r.json().get("data") or {}
        assert "released" in data, f"Missing 'released' in response: {data}"
        assert isinstance(data["released"], int)

    def test_expire_reservations_sales_forbidden(self, sales1):
        r = sales1.post(f"{API}/deals/expire-reservations", json={})
        assert r.status_code == 403, f"Expected 403 for sales, got {r.status_code}: {r.text}"


# ==================== INDEXES ====================

class TestIndexes:
    def test_indexes_exist(self, admin):
        """Verify via direct mongo connection that required indexes exist."""
        try:
            from pymongo import MongoClient
        except Exception:
            pytest.skip("pymongo not installed")
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "test_database")
        client = MongoClient(mongo_url, serverSelectionTimeoutMS=2000)
        db = client[db_name]

        def has_idx(coll, key):
            try:
                idx = db[coll].index_information()
            except Exception:
                return False
            for _, spec in idx.items():
                keys = [k for k, _ in spec.get("key", [])]
                if key in keys:
                    return True
            return False

        assert has_idx("tasks", "source_event"), "tasks.source_event index missing"
        assert has_idx("tasks", "related_entity_id"), "tasks.related_entity_id index missing"
        assert has_idx("tasks", "due_date"), "tasks.due_date index missing"
        assert has_idx("deals", "reserved_until"), "deals.reserved_until index missing"
        assert has_idx("events", "entity_id"), "events.entity_id index missing"
        assert has_idx("appointments", "lead_id"), "appointments.lead_id index missing"


# ==================== COOKIE SECURITY ====================

class TestCookieFlags:
    def test_login_sets_cookies_with_dev_flags(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": "admin@sipro.com", "password": "admin123"})
        assert r.status_code == 200, r.text
        # Pull raw Set-Cookie headers (could be multiple)
        raw_cookies = []
        if hasattr(r.raw.headers, "getlist"):
            raw_cookies = r.raw.headers.getlist("Set-Cookie")
        else:
            raw_cookies = [r.headers.get("Set-Cookie", "")]

        # Find app's access_token cookie (ignore proxy cookies like __cf_bm)
        app_cookies = [c for c in raw_cookies if c.lower().startswith("access_token=") or c.lower().startswith("refresh_token=")]
        assert app_cookies, f"App cookies not set. raw: {raw_cookies!r}"

        for c in app_cookies:
            low = c.lower()
            # Must be httponly
            assert "httponly" in low, f"App cookie missing HttpOnly: {c!r}"
            # COOKIE_SECURE=false in dev → must NOT have Secure attribute on app cookies
            # Use word-boundary-ish check: '; secure' or '; secure;' or trailing
            parts = [p.strip() for p in c.split(";")]
            assert "secure" not in [p.lower() for p in parts], f"App cookie marked Secure in dev: {c!r}"
            # SameSite should be lax in dev (COOKIE_SECURE=false)
            assert "samesite=lax" in low, f"App cookie samesite!=lax in dev: {c!r}"


# ==================== BACKFILL ====================

class TestBackfill:
    def test_no_leads_missing_first_contacted_at_when_last_contacted_set(self, admin):
        # All leads with last_contacted_at set should have first_contacted_at set as well
        r = admin.get(f"{API}/leads", params={"limit": 500})
        assert r.status_code == 200, r.text
        items = r.json().get("data") or []
        offenders = [it for it in items
                     if it.get("last_contacted_at") and not it.get("first_contacted_at")]
        assert not offenders, f"{len(offenders)} leads still missing first_contacted_at after backfill"
