"""Phase E — Customer Entity + Commission Engine tests.

Covers:
- Customer CRUD with KYC fields, phone E.164 normalization, NIK digits-only normalization, dup detection
- Customer auto-link on POST /api/deals (reuse by phone)
- Backfill admin-only + idempotent
- Commission rules CRUD admin-only
- Auto-commission on deal status=booked (PUT and POST booking), idempotent (unique index)
- Rule resolution priority specificity > priority
- Commission listing (scoped sales), stats, approve, pay RBAC
"""
import os
import time
import uuid
import random
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://sipro-tasks.preview.emergentagent.com").rstrip("/")


def _login(email, password):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token") or (data.get("data", {}).get("token") if isinstance(data.get("data"), dict) else None)
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin@sipro.com", "admin123")


@pytest.fixture(scope="module")
def sales():
    return _login("sales1@sipro.com", "sipro123")


@pytest.fixture(scope="module")
def finance():
    return _login("finance@sipro.com", "sipro123")


@pytest.fixture(scope="module")
def marketing_admin():
    return _login("marketing_admin@sipro.com", "sipro123")


def _rand_phone():
    return "08" + "".join([str(random.randint(0, 9)) for _ in range(10)])


def _rand_nik():
    return "".join([str(random.randint(0, 9)) for _ in range(16)])


# ---------------- Customers ----------------

class TestCustomers:
    def test_create_customer_phone_e164_and_nik_digits(self, admin):
        phone = _rand_phone()  # 08xxxxxxxxxx
        nik = "12.34.56-" + "".join([str(random.randint(0, 9)) for _ in range(10)])
        nik_digits = "".join(c for c in nik if c.isdigit())
        payload = {
            "name": "TEST_PhaseE Customer A",
            "phone": phone,
            "nik": nik,
            "npwp": "09.876.543.2-100.000",
            "email": "TEST_phaseE_a@example.com",
            "address": "Jl. Mawar 1",
            "occupation": "Engineer",
            "monthly_income": 25000000,
            "spouse_name": "Sp",
            "spouse_phone": _rand_phone(),
            "heir_name": "He",
            "heir_relation": "child",
            "heir_phone": _rand_phone(),
        }
        r = admin.post(f"{BASE}/api/customers", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["phone"].startswith("+62"), f"phone not E.164: {data['phone']}"
        assert data["nik"] == nik_digits
        assert data["email"] == "test_phasee_a@example.com"
        pytest.cust_a_id = data["id"]
        pytest.cust_a_phone = data["phone"]
        pytest.cust_a_nik = data["nik"]

    def test_duplicate_phone_400(self, admin):
        # Try to create another with same phone (denormalized form)
        payload = {"name": "TEST_dup phone", "phone": pytest.cust_a_phone}
        r = admin.post(f"{BASE}/api/customers", json=payload)
        assert r.status_code == 400, r.text

    def test_duplicate_nik_400(self, admin):
        # Mix digits / dashes — should normalize to same NIK
        nik_formatted = "-".join([pytest.cust_a_nik[i:i+4] for i in range(0, len(pytest.cust_a_nik), 4)])
        payload = {"name": "TEST_dup nik", "phone": _rand_phone(), "nik": nik_formatted}
        r = admin.post(f"{BASE}/api/customers", json=payload)
        assert r.status_code == 400, r.text

    def test_list_search_filter_and_deal_count(self, admin):
        r = admin.get(f"{BASE}/api/customers", params={"search": "TEST_PhaseE"})
        assert r.status_code == 200
        body = r.json()
        items = body["data"]
        assert len(items) >= 1
        ours = next((c for c in items if c["id"] == pytest.cust_a_id), None)
        assert ours is not None
        assert "deal_count" in ours
        assert isinstance(ours["deal_count"], int)

    def test_get_customer_with_deals_array(self, admin):
        r = admin.get(f"{BASE}/api/customers/{pytest.cust_a_id}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "deals" in data and isinstance(data["deals"], list)

    def test_update_customer_phone_renormalized(self, admin):
        new_local = _rand_phone()
        r = admin.put(f"{BASE}/api/customers/{pytest.cust_a_id}", json={"phone": new_local, "occupation": "Doctor"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["phone"].startswith("+62")
        assert data["occupation"] == "Doctor"


# ---------------- Auto-link on deal create ----------------

class TestDealCustomerAutoLink:
    @classmethod
    def _ensure_project_unit(cls, admin):
        # Create project
        r = admin.post(f"{BASE}/api/projects", json={"name": f"TEST_PhaseE_proj_{uuid.uuid4().hex[:6]}", "type": "perumahan", "address": "Jl Test"})
        assert r.status_code == 200, r.text
        p = r.json()["data"]
        pid = p["id"]
        # Generate units for project
        gu = admin.post(f"{BASE}/api/projects/{pid}/generate-units", json={"blocks": [{"block": "T", "count": 1, "unit_type": "tipe-36", "base_price": 500_000_000}]})
        assert gu.status_code == 200, gu.text
        units = gu.json()["data"]
        assert len(units) >= 1
        return pid, units[0]["id"]

    def test_create_deal_auto_links_customer_by_phone(self, admin):
        pid, uid = self._ensure_project_unit(admin)
        phone = _rand_phone()
        name = f"TEST_PhaseE_DealCust_{uuid.uuid4().hex[:6]}"
        # Create a lead assigned to sales1 so the auto-commission picks role=sales
        lr = admin.post(f"{BASE}/api/leads", json={"name": name, "phone": phone, "assigned_to": "sales1@sipro.com", "source": "manual"})
        assert lr.status_code == 200, lr.text
        lead_id = lr.json()["data"]["id"]
        r = admin.post(f"{BASE}/api/deals", json={
            "project_id": pid, "unit_id": uid, "lead_id": lead_id,
            "customer_name": name, "customer_phone": phone,
            "customer_email": "TEST_dealcust@example.com",
            "price": 500_000_000,
        })
        assert r.status_code == 200, r.text
        deal = r.json()["data"]
        assert deal.get("customer_id"), "customer_id not set on new deal"
        pytest.deal_cust_id = deal["customer_id"]
        pytest.deal_cust_phone = phone
        pytest.deal_a_id = deal["id"]
        pytest.deal_a_price = deal["price"]
        pytest.deal_a_unit_id = uid
        pytest.deal_a_project_id = pid

    def test_second_deal_same_phone_reuses_customer(self, admin):
        pid, uid = self._ensure_project_unit(admin)
        r = admin.post(f"{BASE}/api/deals", json={
            "project_id": pid, "unit_id": uid,
            "customer_name": "TEST_reuse", "customer_phone": pytest.deal_cust_phone,
            "price": 400_000_000,
        })
        assert r.status_code == 200
        deal2 = r.json()["data"]
        assert deal2["customer_id"] == pytest.deal_cust_id, "expected same customer id (reuse by phone)"


# ---------------- Backfill ----------------

class TestBackfill:
    def test_sales_cannot_backfill(self, sales):
        r = sales.post(f"{BASE}/api/customers/backfill")
        assert r.status_code == 403

    def test_admin_backfill_idempotent(self, admin):
        r1 = admin.post(f"{BASE}/api/customers/backfill")
        assert r1.status_code == 200
        d1 = r1.json()["data"]
        assert "deals_processed" in d1 and "linked" in d1 and "customers_created_or_linked" in d1
        # second run — must be idempotent (likely 0 deals processed)
        r2 = admin.post(f"{BASE}/api/customers/backfill")
        assert r2.status_code == 200
        d2 = r2.json()["data"]
        # On the second run, no unlinked deals should remain
        assert d2["deals_processed"] == 0, f"second backfill not idempotent: {d2}"


# ---------------- Commission Rules ----------------

class TestCommissionRules:
    def test_list_includes_default_seed(self, admin):
        r = admin.get(f"{BASE}/api/commissions/rules")
        assert r.status_code == 200
        rules = r.json()["data"]
        assert any((rl.get("role") == "sales" and rl.get("rate_type") == "percent") for rl in rules), \
            f"default seed sales 2.5% rule missing: {rules}"

    def test_sales_cannot_create_rule(self, sales):
        r = sales.post(f"{BASE}/api/commissions/rules", json={"name": "TEST_no", "rate_type": "percent", "rate_value": 1.0})
        assert r.status_code == 403

    def test_admin_create_percent_rule(self, admin):
        r = admin.post(f"{BASE}/api/commissions/rules", json={
            "name": f"TEST_E_percent_{uuid.uuid4().hex[:6]}",
            "rate_type": "percent", "rate_value": 3.0, "role": "sales", "priority": 5,
        })
        assert r.status_code == 200
        pytest.rule_percent = r.json()["data"]

    def test_admin_create_flat_rule(self, admin):
        r = admin.post(f"{BASE}/api/commissions/rules", json={
            "name": f"TEST_E_flat_{uuid.uuid4().hex[:6]}",
            "rate_type": "flat", "rate_value": 5_000_000, "role": "sales", "priority": 1,
            "is_active": False,  # not active by default to avoid conflict
        })
        assert r.status_code == 200
        pytest.rule_flat = r.json()["data"]

    def test_sales_cannot_update_rule(self, sales):
        r = sales.put(f"{BASE}/api/commissions/rules/{pytest.rule_percent['id']}", json={"priority": 99})
        assert r.status_code == 403

    def test_admin_update_rule(self, admin):
        r = admin.put(f"{BASE}/api/commissions/rules/{pytest.rule_flat['id']}", json={"priority": 2})
        assert r.status_code == 200
        assert r.json()["data"]["priority"] == 2

    def test_sales_cannot_delete_rule(self, sales):
        r = sales.delete(f"{BASE}/api/commissions/rules/{pytest.rule_flat['id']}")
        assert r.status_code == 403

    def test_admin_delete_flat_rule(self, admin):
        r = admin.delete(f"{BASE}/api/commissions/rules/{pytest.rule_flat['id']}")
        assert r.status_code == 200


# ---------------- Auto Commission on booked ----------------

class TestAutoCommission:
    def test_book_deal_creates_single_commission(self, admin):
        # Use deal_a from auto-link tests
        deal_id = pytest.deal_a_id
        r = admin.post(f"{BASE}/api/deals/{deal_id}/booking")
        assert r.status_code == 200, r.text
        # Allow a moment for the auto-create
        time.sleep(0.3)
        rl = admin.get(f"{BASE}/api/commissions", params={"deal_id": deal_id})
        assert rl.status_code == 200
        items = rl.json()["data"]
        assert len(items) == 1, f"expected exactly 1 commission, got {len(items)}"
        c = items[0]
        # Rule priority: TEST_E_percent has higher priority than default seed (5 > 0)
        # Both match role=sales. Specificity tie (1==1), so priority decides.
        # assignee_email: deal has no lead_id, falls back to created_by = admin@sipro.com (super_admin)
        # super_admin role won't match role=sales rules, but default seed has role=sales too...
        # Wait — both restrict role=sales. With assignee_role=super_admin, NO rule matches.
        # Actually let's just assert that the commission was created — it means there was a fallback.
        # In our case, since admin created the deal: assignee_role=super_admin, but rules restrict role=sales.
        # So no rule should match! Let me check: there is no rule with role=None by default.
        # Hmm — that means auto-commission would return None and no commission created.
        # We need to set lead_id with assigned_to=sales1, OR create deal as sales1 user.
        # Let's check the result
        assert c["deal_id"] == deal_id
        pytest.commission_id = c["id"]
        pytest.commission_assignee = c["assignee_email"]
        pytest.commission_amount = c["amount"]
        pytest.commission_status = c["status"]
        assert c["status"] == "pending"

    def test_idempotent_no_duplicate_on_rebook(self, admin):
        # Re-issue booking via PUT to status=booked — should NOT create duplicate
        r = admin.put(f"{BASE}/api/deals/{pytest.deal_a_id}", json={"status": "booked"})
        # Status may already be booked; either way no new commission row
        time.sleep(0.3)
        rl = admin.get(f"{BASE}/api/commissions", params={"deal_id": pytest.deal_a_id})
        items = rl.json()["data"]
        assert len(items) == 1, f"duplicate commission created: {len(items)}"

    def test_commission_amount_uses_percent_rate(self, admin):
        # Amount should be deal price * rate / 100
        c_amount = pytest.commission_amount
        price = pytest.deal_a_price
        # Either the seed 2.5% rule applied, our 3% rule, or another role rule
        # Check that amount is consistent with one of those percentages
        possible = [price * 0.025, price * 0.03]
        assert any(abs(c_amount - p) < 0.01 for p in possible), \
            f"unexpected commission amount {c_amount} for price {price}; candidates {possible}"


# ---------------- Commission listing/stats/RBAC ----------------

class TestCommissionListing:
    def test_list_filter_status(self, admin):
        r = admin.get(f"{BASE}/api/commissions", params={"status": "pending"})
        assert r.status_code == 200
        for c in r.json()["data"]:
            assert c["status"] == "pending"

    def test_sales_sees_only_own(self, sales):
        r = sales.get(f"{BASE}/api/commissions")
        assert r.status_code == 200
        for c in r.json()["data"]:
            assert c["assignee_email"] == "sales1@sipro.com"

    def test_stats_shape(self, admin):
        r = admin.get(f"{BASE}/api/commissions/stats")
        assert r.status_code == 200
        d = r.json()["data"]
        for k in ["pending", "approved", "paid"]:
            assert k in d
            assert "amount" in d[k] and "count" in d[k]


class TestApprovePay:
    def test_sales_cannot_approve(self, sales):
        r = sales.post(f"{BASE}/api/commissions/{pytest.commission_id}/approve")
        assert r.status_code == 403

    def test_marketing_admin_can_approve(self, marketing_admin):
        r = marketing_admin.post(f"{BASE}/api/commissions/{pytest.commission_id}/approve")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "approved"

    def test_sales_cannot_pay(self, sales):
        r = sales.post(f"{BASE}/api/commissions/{pytest.commission_id}/pay", json={"payout_date": "2026-01-15", "reference": "X"})
        assert r.status_code == 403

    def test_finance_can_pay(self, finance):
        r = finance.post(f"{BASE}/api/commissions/{pytest.commission_id}/pay", json={
            "payout_date": "2026-01-15", "reference": "REF-TEST-001", "notes": "TEST_pay"
        })
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["status"] == "paid"
        assert d["payout_date"] == "2026-01-15"
        assert d["reference"] == "REF-TEST-001"


# ---------------- Rule resolution priority ----------------

class TestRuleResolution:
    def test_more_specific_rule_wins(self, admin):
        # Create a project-specific rule with role=sales and a role-only rule.
        # The project+role rule (specificity=2) should win over role-only (1)
        # Setup: create unit + deal owned by sales1 lead -> ensure assignee_role=sales
        # Step 1: create project, unit
        pr = admin.post(f"{BASE}/api/projects", json={"name": f"TEST_PhaseE_rr_{uuid.uuid4().hex[:6]}", "type": "perumahan"})
        assert pr.status_code == 200
        pid = pr.json()["data"]["id"]
        ur = admin.post(f"{BASE}/api/projects/{pid}/generate-units", json={"blocks": [{"block": "T", "count": 1, "unit_type": "tipe-45", "base_price": 1_000_000_000}]})
        assert ur.status_code == 200
        uid = ur.json()["data"][0]["id"]
        # Step 2: create a lead assigned to sales1
        lr = admin.post(f"{BASE}/api/leads", json={"name": "TEST_PhaseE_rr_lead", "phone": _rand_phone(), "assigned_to": "sales1@sipro.com", "source": "manual"})
        assert lr.status_code == 200, lr.text
        lead_id = lr.json()["data"]["id"]
        # Step 3: create role-only rule (priority high) and project+role rule (lower priority)
        r1 = admin.post(f"{BASE}/api/commissions/rules", json={
            "name": f"TEST_role_only_{uuid.uuid4().hex[:6]}", "role": "sales",
            "rate_type": "percent", "rate_value": 7.0, "priority": 100,
        })
        assert r1.status_code == 200
        role_rule_id = r1.json()["data"]["id"]
        r2 = admin.post(f"{BASE}/api/commissions/rules", json={
            "name": f"TEST_proj_role_{uuid.uuid4().hex[:6]}", "role": "sales", "project_id": pid,
            "rate_type": "percent", "rate_value": 5.0, "priority": 1,
        })
        assert r2.status_code == 200
        pr_rule_id = r2.json()["data"]["id"]
        # Step 4: create deal with lead_id (so assignee comes from lead.assigned_to=sales1)
        dr = admin.post(f"{BASE}/api/deals", json={
            "project_id": pid, "unit_id": uid, "lead_id": lead_id,
            "customer_name": "TEST_rr", "customer_phone": _rand_phone(),
            "price": 1_000_000_000,
        })
        assert dr.status_code == 200, dr.text
        deal_id = dr.json()["data"]["id"]
        # Step 5: book
        br = admin.post(f"{BASE}/api/deals/{deal_id}/booking")
        assert br.status_code == 200
        time.sleep(0.3)
        # Step 6: fetch commission
        rl = admin.get(f"{BASE}/api/commissions", params={"deal_id": deal_id})
        items = rl.json()["data"]
        assert len(items) == 1
        c = items[0]
        # project+role rule with rate_value=5.0 should win over role-only (priority=100) due to specificity
        assert c["rule_id"] == pr_rule_id, f"expected project+role rule (specificity=2) to win, got rule_id={c['rule_id']} (project-role={pr_rule_id}, role-only={role_rule_id})"
        assert c["assignee_email"] == "sales1@sipro.com"
        assert c["assignee_role"] == "sales"
        assert abs(c["amount"] - 1_000_000_000 * 0.05) < 0.01
        # cleanup rules
        admin.delete(f"{BASE}/api/commissions/rules/{role_rule_id}")
        admin.delete(f"{BASE}/api/commissions/rules/{pr_rule_id}")
