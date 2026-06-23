"""Iteration 13 tests: AD ANALYTICS (window aggregation + CSV export) +
ad_events logging (impression + click) + inactive-ad guard rails.

Covers:
- GET /api/admin/ads/analytics?days=N (admin + ad-manager + 403 non-admin + 400 bad days)
- GET /api/admin/ads/analytics/export?days=N (CSV with Content-Disposition + TOTAL row + 403)
- POST /api/ads/{id}/impression on ACTIVE ad logs ad_events row with expires_at ~90d
- GET  /api/ads/{id}/click logs ad_events row with kind=click and 302 redirects
- POST /api/ads/{id}/impression on INACTIVE ad does NOT bump counters or log an event
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://bet-esports.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@esportsbet.com"
ADMIN_PASS = "admin123"
USER_EMAIL = "davidjovanic@yahoo.com.au"
USER_PASS = "Andmay123"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ---------- fixtures ----------
def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def user():
    return _login(USER_EMAIL, USER_PASS)


@pytest.fixture(scope="module")
def mongo():
    cli = MongoClient(MONGO_URL)
    yield cli[DB_NAME]
    cli.close()


@pytest.fixture(scope="module")
def davidjovanic_id(mongo):
    u = mongo.users.find_one({"email": USER_EMAIL})
    assert u, "davidjovanic missing"
    return str(u["_id"])


@pytest.fixture(scope="module")
def active_ad(admin):
    """Create a fresh ad and yield its id; clean up at end."""
    name = f"TEST_iter13_{uuid.uuid4().hex[:8]}"
    r = admin.post(f"{API}/admin/ads", json={
        "name": name,
        "image_url": "https://placehold.co/200x140.png",
        "click_url": "https://example.com/iter13",
        "active": True,
    }, timeout=15)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    yield aid
    admin.delete(f"{API}/admin/ads/{aid}", timeout=15)


# ============ AD EVENT LOGGING (impression + click) ============
class TestAdEventLogging:
    def test_impression_increments_and_logs_event(self, active_ad, user, admin, mongo):
        # Read pre counters
        before = next(a for a in admin.get(f"{API}/admin/ads", params={"q": "TEST_iter13_"}, timeout=15).json() if a["id"] == active_ad)
        pre_impr = before["impression_count"]

        r = user.post(f"{API}/ads/{active_ad}/impression", timeout=15)
        assert r.status_code == 200, r.text

        after = next(a for a in admin.get(f"{API}/admin/ads", params={"q": "TEST_iter13_"}, timeout=15).json() if a["id"] == active_ad)
        assert after["impression_count"] == pre_impr + 1

        ev = mongo.ad_events.find_one({"ad_id": active_ad, "kind": "impression"}, sort=[("timestamp", -1)])
        assert ev, "no impression event logged"
        assert ev.get("kind") == "impression"
        assert "timestamp" in ev
        assert "expires_at" in ev, "TTL field missing"
        exp = ev["expires_at"]
        if isinstance(exp, str):
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        else:
            exp_dt = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        delta = exp_dt - datetime.now(timezone.utc)
        assert timedelta(days=85) < delta < timedelta(days=95), f"expires_at not ~90d: {delta}"

    def test_click_redirects_and_logs_event(self, active_ad, admin, mongo):
        before = next(a for a in admin.get(f"{API}/admin/ads", params={"q": "TEST_iter13_"}, timeout=15).json() if a["id"] == active_ad)
        pre_clk = before["click_count"]

        # Anonymous click
        r = requests.get(f"{API}/ads/{active_ad}/click", allow_redirects=False, timeout=15)
        assert r.status_code == 302
        assert "example.com" in r.headers.get("location", "")

        after = next(a for a in admin.get(f"{API}/admin/ads", params={"q": "TEST_iter13_"}, timeout=15).json() if a["id"] == active_ad)
        assert after["click_count"] == pre_clk + 1

        ev = mongo.ad_events.find_one({"ad_id": active_ad, "kind": "click"}, sort=[("timestamp", -1)])
        assert ev, "no click event logged"
        assert "expires_at" in ev


# ============ Inactive-ad guard ============
class TestInactiveAdGuard:
    def test_inactive_impression_no_increment_no_event(self, admin, user, mongo):
        # Create then deactivate a fresh ad
        name = f"TEST_iter13_inactive_{uuid.uuid4().hex[:6]}"
        c = admin.post(f"{API}/admin/ads", json={
            "name": name,
            "image_url": "https://placehold.co/200x140.png",
            "click_url": "https://example.com/inactive",
            "active": False,
        }, timeout=15)
        assert c.status_code == 200, c.text
        aid = c.json()["id"]
        try:
            pre_events = mongo.ad_events.count_documents({"ad_id": aid})
            r = user.post(f"{API}/ads/{aid}/impression", timeout=15)
            assert r.status_code == 200  # endpoint returns ok even when not matched
            # No-op verification
            doc = mongo.advertisements.find_one({"id": aid})
            assert int(doc.get("impression_count", 0)) == 0
            post_events = mongo.ad_events.count_documents({"ad_id": aid})
            assert post_events == pre_events, "ad_events row was logged for an inactive ad"
        finally:
            admin.delete(f"{API}/admin/ads/{aid}", timeout=15)


# ============ ANALYTICS JSON ============
class TestAdsAnalyticsJSON:
    def test_non_admin_403(self, user):
        r = user.get(f"{API}/admin/ads/analytics", params={"days": 7}, timeout=15)
        assert r.status_code == 403

    def test_admin_analytics_default_7d(self, admin, active_ad):
        r = admin.get(f"{API}/admin/ads/analytics", params={"days": 7}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["window_days"] == 7
        assert "totals" in body and "rows" in body
        for k in ("impressions", "clicks", "ctr"):
            assert k in body["totals"]
        # row schema
        if body["rows"]:
            row = next((r0 for r0 in body["rows"] if r0["id"] == active_ad), None)
            assert row, "test ad missing from analytics rows"
            for k in ("id", "name", "active", "click_url", "image_url",
                      "window_impressions", "window_clicks", "window_ctr",
                      "total_impressions", "total_clicks", "total_ctr", "created_at"):
                assert k in row, f"missing {k}"
            # Counters from earlier tests should reflect
            assert row["total_impressions"] >= 1
            assert row["total_clicks"] >= 1

    def test_invalid_days(self, admin):
        r0 = admin.get(f"{API}/admin/ads/analytics", params={"days": 0}, timeout=15)
        assert r0.status_code == 400, r0.text
        r1 = admin.get(f"{API}/admin/ads/analytics", params={"days": 400}, timeout=15)
        assert r1.status_code == 400, r1.text

    def test_ad_manager_can_access(self, admin, user, davidjovanic_id):
        # Promote
        g = admin.post(f"{API}/admin/ad-managers", json={"user_id": davidjovanic_id}, timeout=15)
        assert g.status_code == 200, g.text
        try:
            r = user.get(f"{API}/admin/ads/analytics", params={"days": 7}, timeout=15)
            assert r.status_code == 200, r.text
            assert "rows" in r.json()
        finally:
            admin.delete(f"{API}/admin/ad-managers/{davidjovanic_id}", timeout=15)


# ============ ANALYTICS CSV EXPORT ============
class TestAdsAnalyticsCSV:
    def test_non_admin_csv_403(self, user):
        r = user.get(f"{API}/admin/ads/analytics/export", params={"days": 7}, timeout=15)
        assert r.status_code == 403

    def test_admin_csv_export(self, admin, active_ad):
        r = admin.get(f"{API}/admin/ads/analytics/export", params={"days": 7}, timeout=15)
        assert r.status_code == 200, r.text
        ct = r.headers.get("content-type", "")
        assert "text/csv" in ct, f"wrong content-type: {ct}"
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd and ".csv" in cd, f"missing CD header: {cd}"
        text = r.text
        # Header row
        assert "Ad ID" in text
        assert "Impressions (7d)" in text or "Impressions (7" in text
        assert "CTR % (Total)" in text
        # TOTAL row
        assert "TOTAL" in text
        # Should contain our test ad name or id
        assert active_ad in text


# ============ BACKWARDS COMPAT smoke ============
class TestBackwardsCompat:
    """Quick smoke that key prior-iteration endpoints still respond."""
    def test_rotation_still_works(self, user):
        r = user.get(f"{API}/ads/rotation", timeout=15)
        assert r.status_code == 200

    def test_admin_ads_list_still_works(self, admin):
        r = admin.get(f"{API}/admin/ads", timeout=15)
        assert r.status_code == 200

    def test_admin_latency_dashboard_still_works(self, admin):
        r = admin.get(f"{API}/admin/latency/dashboard", timeout=15)
        assert r.status_code == 200

    def test_auth_me_still_includes_can_manage_ads(self, admin):
        r = admin.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert "can_manage_ads" in r.json()
