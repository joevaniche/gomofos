"""Iteration 12 tests: ADS platform + ad-manager flag + admin latency dashboard/graphs.

Covers:
- /api/admin/ads CRUD (admin + ad-manager + non-admin gating)
- /api/ads/rotation (active-only) + /api/ads/{id}/click 302 + /api/ads/{id}/impression
- /api/admin/ad-managers grant/list/revoke
- /api/admin/latency/{tournament|competition}/{id} + dashboard + extend-retention
- /api/tournaments/{id}/latency persists expires_at
- /api/auth/me includes can_manage_ads
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


# ---------- helpers / fixtures ----------
def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
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
    assert u, "davidjovanic user not present in DB"
    return str(u["_id"])


# ============ AUTH / UserResponse ============
class TestAuthMe:
    def test_admin_me_includes_can_manage_ads(self, admin):
        r = admin.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "can_manage_ads" in body, body
        # admin is implicitly an ad admin via role check but flag may be False
        assert body.get("role") == "admin"

    def test_user_me_default_false(self, user):
        r = user.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("can_manage_ads") in (False, None)


# ============ ADS — admin CRUD + permissions ============
class TestAdminAdsCRUD:
    created_ad_id = None

    def test_non_admin_cannot_create(self, user):
        r = user.post(f"{API}/admin/ads", json={
            "name": "TEST_ad_block",
            "image_url": "https://example.com/x.png",
            "click_url": "https://example.com",
        }, timeout=15)
        assert r.status_code == 403, r.text

    def test_admin_create_ad(self, admin):
        name = f"TEST_ad_{uuid.uuid4().hex[:8]}"
        r = admin.post(f"{API}/admin/ads", json={
            "name": name,
            "image_url": "https://placehold.co/200x200.png",
            "click_url": "https://example.com/landing",
            "active": True,
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == name
        assert data["click_url"].startswith("https://")
        assert data["active"] is True
        assert data["click_count"] == 0
        assert data["impression_count"] == 0
        assert "id" in data
        TestAdminAdsCRUD.created_ad_id = data["id"]

    def test_admin_list_filter(self, admin):
        assert TestAdminAdsCRUD.created_ad_id
        r = admin.get(f"{API}/admin/ads", params={"q": "TEST_ad_"}, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert any(a["id"] == TestAdminAdsCRUD.created_ad_id for a in items)

    def test_admin_list_case_insensitive(self, admin):
        r = admin.get(f"{API}/admin/ads", params={"q": "test_AD_"}, timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert any(a["id"] == TestAdminAdsCRUD.created_ad_id for a in items)

    def test_admin_patch_ad(self, admin):
        aid = TestAdminAdsCRUD.created_ad_id
        r = admin.patch(f"{API}/admin/ads/{aid}", json={
            "name": "TEST_ad_renamed",
            "image_url": "https://placehold.co/200x200.png",
            "click_url": "https://example.com/landing2",
            "active": False,
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == "TEST_ad_renamed"
        assert d["active"] is False

    def test_rotation_excludes_inactive(self, user):
        aid = TestAdminAdsCRUD.created_ad_id
        r = user.get(f"{API}/ads/rotation", timeout=15)
        assert r.status_code == 200
        assert all(a["id"] != aid for a in r.json())

    def test_reactivate_and_rotation_includes(self, admin, user):
        aid = TestAdminAdsCRUD.created_ad_id
        admin.patch(f"{API}/admin/ads/{aid}", json={
            "name": "TEST_ad_renamed",
            "image_url": "https://placehold.co/200x200.png",
            "click_url": "https://example.com/landing2",
            "active": True,
        }, timeout=15)
        r = user.get(f"{API}/ads/rotation", timeout=15)
        assert any(a["id"] == aid for a in r.json())

    def test_click_redirects_and_increments(self, admin):
        aid = TestAdminAdsCRUD.created_ad_id
        # use a session with no auth to confirm public access
        r = requests.get(f"{API}/ads/{aid}/click", allow_redirects=False, timeout=15)
        assert r.status_code == 302
        assert "example.com" in r.headers.get("location", "")
        # verify counter
        r2 = admin.get(f"{API}/admin/ads", params={"q": "TEST_ad_"}, timeout=15)
        items = r2.json()
        match = next(a for a in items if a["id"] == aid)
        assert match["click_count"] >= 1

    def test_impression_increments(self, user, admin):
        aid = TestAdminAdsCRUD.created_ad_id
        r = user.post(f"{API}/ads/{aid}/impression", timeout=15)
        assert r.status_code == 200
        r2 = admin.get(f"{API}/admin/ads", params={"q": "TEST_ad_"}, timeout=15)
        match = next(a for a in r2.json() if a["id"] == aid)
        assert match["impression_count"] >= 1

    def test_admin_delete(self, admin):
        aid = TestAdminAdsCRUD.created_ad_id
        r = admin.delete(f"{API}/admin/ads/{aid}", timeout=15)
        assert r.status_code == 200
        # gone
        r2 = admin.get(f"{API}/admin/ads", params={"q": "TEST_ad_renamed"}, timeout=15)
        assert all(a["id"] != aid for a in r2.json())


# ============ AD-MANAGER role ============
class TestAdManager:
    def test_non_admin_cannot_list_managers(self, user):
        r = user.get(f"{API}/admin/ad-managers", timeout=15)
        assert r.status_code == 403

    def test_non_admin_cannot_grant(self, user, davidjovanic_id):
        r = user.post(f"{API}/admin/ad-managers", json={"user_id": davidjovanic_id}, timeout=15)
        assert r.status_code == 403

    def test_admin_grants_and_user_can_manage_ads(self, admin, user, davidjovanic_id, mongo):
        # grant
        r = admin.post(f"{API}/admin/ad-managers", json={"user_id": davidjovanic_id}, timeout=15)
        assert r.status_code == 200, r.text

        # /auth/me should now reflect can_manage_ads=True (re-login to refresh stored claims if any)
        me = user.get(f"{API}/auth/me", timeout=15).json()
        # If session is cached, allow direct DB read fallback. Endpoint reads from DB so should be true.
        assert me.get("can_manage_ads") is True, me

        # The promoted user should now be able to create an ad
        name = f"TEST_admgr_{uuid.uuid4().hex[:6]}"
        r2 = user.post(f"{API}/admin/ads", json={
            "name": name,
            "image_url": "https://placehold.co/200x200.png",
            "click_url": "https://example.com/promoted",
        }, timeout=15)
        assert r2.status_code == 200, r2.text
        # clean up created ad
        admin.delete(f"{API}/admin/ads/{r2.json()['id']}", timeout=15)

    def test_admin_list_includes_promoted(self, admin, davidjovanic_id):
        r = admin.get(f"{API}/admin/ad-managers", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert any(i["id"] == davidjovanic_id and i["can_manage_ads"] for i in items)

    def test_ad_manager_cannot_access_disputes_or_user_admin(self, user):
        # escalation boundary: still no admin elsewhere
        r1 = user.get(f"{API}/admin/disputes", timeout=15)
        assert r1.status_code == 403
        r2 = user.get(f"{API}/admin/ad-managers", timeout=15)
        assert r2.status_code == 403  # ad-manager flag does NOT grant role mgmt
        r3 = user.get(f"{API}/admin/latency/dashboard", timeout=15)
        assert r3.status_code == 403

    def test_admin_revoke(self, admin, user, davidjovanic_id):
        r = admin.delete(f"{API}/admin/ad-managers/{davidjovanic_id}", timeout=15)
        assert r.status_code == 200
        me = user.get(f"{API}/auth/me", timeout=15).json()
        assert me.get("can_manage_ads") in (False, None)


# ============ Admin latency ============
class TestAdminLatency:
    def test_non_admin_dashboard_403(self, user):
        r = user.get(f"{API}/admin/latency/dashboard", timeout=15)
        assert r.status_code == 403

    def test_admin_dashboard(self, admin):
        r = admin.get(f"{API}/admin/latency/dashboard", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "thresholds" in body
        assert "items" in body
        assert "warn" in body["thresholds"] and "high" in body["thresholds"]
        # Disputed items must come first
        disputed_seen = True
        for it in body["items"]:
            if not it["is_disputed"]:
                disputed_seen = False
            else:
                assert disputed_seen, "non-disputed item appeared before a disputed one"

    def test_dashboard_search_filter(self, admin):
        # Use a string very unlikely to match (control)
        r = admin.get(f"{API}/admin/latency/dashboard", params={"q": "zzzzzz_no_match"}, timeout=15)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 0

    def test_tournament_404_for_bad_id(self, admin):
        bad_id = "0" * 24  # valid ObjectId shape
        r = admin.get(f"{API}/admin/latency/tournament/{bad_id}", timeout=15)
        assert r.status_code == 404

    def test_tournament_404_for_invalid_objectid(self, admin):
        r = admin.get(f"{API}/admin/latency/tournament/not-an-objectid", timeout=15)
        assert r.status_code == 404

    def test_non_admin_tournament_graph_403(self, user, mongo):
        # pick any tournament id present in DB; fallback to bogus
        t = mongo.tournament_latency.find_one({})
        tid = t["tournament_id"] if t else "0" * 24
        r = user.get(f"{API}/admin/latency/tournament/{tid}", timeout=15)
        assert r.status_code == 403

    def test_existing_tournament_graph_has_series_structure(self, admin, mongo):
        from bson import ObjectId
        tid = None
        for cand in mongo.tournament_latency.distinct("tournament_id"):
            try:
                if mongo.tournaments.find_one({"_id": ObjectId(cand)}):
                    tid = cand
                    break
            except Exception:
                continue
        if not tid:
            pytest.skip("no tournament_latency samples with surviving tournament")
        r = admin.get(f"{API}/admin/latency/tournament/{tid}", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "thresholds" in body
        assert "series" in body
        if body["series"]:
            s0 = body["series"][0]
            for k in ("user_id", "username", "points", "avg_ms", "max_ms", "status"):
                assert k in s0
            assert s0["status"] in ("ok", "warn", "high")
            if s0["points"]:
                p = s0["points"][0]
                assert "t" in p and "ms" in p


# ============ Tournament latency persist expires_at + retention extension ============
class TestLatencyPersistExpires:
    def test_post_latency_sets_expires_at(self, user, mongo):
        """POST a fresh latency sample for any tournament where davidjovanic participates,
        then verify a recently-inserted sample carries expires_at."""
        # Find a tournament with davidjovanic accepted/joined
        david = mongo.users.find_one({"email": USER_EMAIL})
        david_id = str(david["_id"])
        t = mongo.tournaments.find_one({"participants.user_id": david_id})
        if not t:
            pytest.skip("davidjovanic not in any tournament with latency endpoint accessible")
        tid = str(t["_id"])
        r = user.post(f"{API}/tournaments/{tid}/latency", params={"latency_ms": 42}, timeout=15)
        # Allow either 200 or non-200 (e.g. tournament not in_progress) — we only check persistence when accepted
        if r.status_code != 200:
            pytest.skip(f"latency POST not accepted (status={r.status_code}); cannot verify expires_at on this tournament")
        # Find the latest sample for (tid, david_id)
        sample = mongo.tournament_latency.find_one(
            {"tournament_id": tid, "user_id": david_id},
            sort=[("timestamp", -1)]
        )
        assert sample, "no sample persisted"
        assert "expires_at" in sample, "expires_at field missing — TTL won't work"
        # expires_at should be roughly 30 days from now
        exp = sample["expires_at"]
        if isinstance(exp, str):
            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        else:
            exp_dt = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        delta = exp_dt - datetime.now(timezone.utc)
        assert timedelta(days=25) < delta < timedelta(days=35), f"expires_at not ~30 days: {delta}"

    def test_extend_retention_validates_days(self, admin, mongo):
        t = mongo.tournament_latency.find_one({})
        if not t:
            pytest.skip("no tournament_latency samples")
        tid = t["tournament_id"]
        r = admin.post(f"{API}/admin/latency/tournament/{tid}/extend-retention", params={"days": 0}, timeout=15)
        assert r.status_code == 400
        r2 = admin.post(f"{API}/admin/latency/tournament/{tid}/extend-retention", params={"days": 900}, timeout=15)
        assert r2.status_code == 400

    def test_extend_retention_updates(self, admin, mongo):
        from bson import ObjectId
        tid = None
        for cand in mongo.tournament_latency.distinct("tournament_id"):
            try:
                if mongo.tournaments.find_one({"_id": ObjectId(cand)}):
                    tid = cand
                    break
            except Exception:
                continue
        if not tid:
            pytest.skip("no tournament_latency samples with surviving tournament")
        r = admin.post(f"{API}/admin/latency/tournament/{tid}/extend-retention", params={"days": 90}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["updated_samples"] >= 1
        # tournament doc has retention marker
        from bson import ObjectId
        td = mongo.tournaments.find_one({"_id": ObjectId(tid)})
        assert td.get("latency_retention_extended_until")

    def test_non_admin_cannot_extend(self, user, mongo):
        t = mongo.tournament_latency.find_one({})
        if not t:
            pytest.skip("no tournament_latency samples")
        tid = t["tournament_id"]
        r = user.post(f"{API}/admin/latency/tournament/{tid}/extend-retention", params={"days": 90}, timeout=15)
        assert r.status_code == 403
