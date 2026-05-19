"""Smoke tests for refactored router endpoints — verify routing intact after server.py split."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@sipro.com", "password": "admin123"})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def sales_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "sales1@sipro.com", "password": "sipro123"})
    assert r.status_code == 200, f"sales1 login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def finance_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "finance@sipro.com", "password": "sipro123"})
    assert r.status_code == 200, f"finance login failed: {r.status_code} {r.text}"
    return s


# auth (still in server.py)
class TestAuth:
    def test_login(self, admin_session):
        r = admin_session.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "admin@sipro.com"

    def test_refresh(self, admin_session):
        r = admin_session.post(f"{API}/auth/refresh")
        assert r.status_code in (200, 204)


# dashboard router
class TestDashboardRouter:
    def test_dashboard_returns_counters(self, admin_session):
        r = admin_session.get(f"{API}/dashboard")
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        # response is {data: {leads, deals, projects, ...}} or flat
        inner = data.get("data", data)
        for key in ("leads", "deals"):
            assert key in inner, f"missing {key} in {list(inner.keys())}"


# construction router
class TestConstructionRouter:
    def test_units_list(self, admin_session):
        r = admin_session.get(f"{API}/construction/units")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))

    def test_summary(self, admin_session):
        r = admin_session.get(f"{API}/construction/summary")
        assert r.status_code == 200, r.text


# finance router
class TestFinanceRouter:
    def test_billing(self, admin_session):
        r = admin_session.get(f"{API}/finance/billing")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))

    def test_payments(self, finance_session):
        r = finance_session.get(f"{API}/finance/payments")
        assert r.status_code == 200, r.text

    def test_finance_summary(self, admin_session):
        r = admin_session.get(f"{API}/finance/summary")
        assert r.status_code == 200, r.text


# notifications router
class TestNotificationsRouter:
    def test_get_notifications(self, admin_session):
        r = admin_session.get(f"{API}/notifications")
        assert r.status_code == 200, r.text

    def test_followup_rules(self, admin_session):
        r = admin_session.get(f"{API}/notifications/auto-rules")
        assert r.status_code == 200, r.text


# whatsapp router
class TestWhatsappRouter:
    def test_messages(self, admin_session):
        r = admin_session.get(f"{API}/whatsapp/messages")
        assert r.status_code == 200, r.text

    def test_templates(self, admin_session):
        r = admin_session.get(f"{API}/whatsapp/templates")
        assert r.status_code == 200, r.text


# dev-report router
class TestDevReportRouter:
    def test_dev_report_items(self, admin_session):
        r = admin_session.get(f"{API}/dev-report")
        assert r.status_code == 200, r.text


# siteplan router
class TestSiteplanRouter:
    def test_siteplan_for_project(self, admin_session):
        # Pick first project
        pj = admin_session.get(f"{API}/projects").json()
        projects = pj if isinstance(pj, list) else pj.get("data", [])
        if not projects:
            pytest.skip("no project to test siteplan")
        pid = projects[0].get("id") or projects[0].get("_id")
        r = admin_session.get(f"{API}/siteplan/{pid}")
        assert r.status_code in (200, 404), r.text  # 404 if no siteplan defined yet is acceptable


# customers router (Phase E)
class TestCustomersRouter:
    def test_list_customers(self, admin_session):
        r = admin_session.get(f"{API}/customers")
        assert r.status_code == 200, r.text


# commissions router (Phase E)
class TestCommissionsRouter:
    def test_list_commissions(self, admin_session):
        r = admin_session.get(f"{API}/commissions")
        assert r.status_code == 200, r.text

    def test_commission_stats(self, admin_session):
        r = admin_session.get(f"{API}/commissions/stats")
        assert r.status_code == 200, r.text

    def test_commission_rules(self, admin_session):
        r = admin_session.get(f"{API}/commissions/rules")
        assert r.status_code == 200, r.text


# leads (still in server.py)
class TestLeadsServer:
    def test_list_leads(self, admin_session):
        r = admin_session.get(f"{API}/leads")
        assert r.status_code == 200, r.text


# deals (still in server.py)
class TestDealsServer:
    def test_list_deals(self, admin_session):
        r = admin_session.get(f"{API}/deals")
        assert r.status_code == 200, r.text

    def test_expire_reservations_admin(self, admin_session):
        r = admin_session.post(f"{API}/deals/expire-reservations")
        assert r.status_code == 200, r.text
