"""Iter14 smoke + frontend HTML meta spot-checks.

This iteration ONLY changed the frontend (nav layout, admin dropdown, terms /
privacy pages, wallet refer button) and the public index.html meta tags.

Backend spot-check confirms there were no regressions to:
- GET /api/auth/me
- POST /api/admin/ads (admin success, non-admin 403)
- GET /api/admin/ads/analytics (admin + ad-manager success)
- GET /api/health/time

Plus a head-only check of the served /index.html to confirm description /
og: / twitter:card meta tags landed.
"""

import os
import re
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bet-esports.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@esportsbet.com"
ADMIN_PASSWORD = "admin123"
USER_EMAIL = "davidjovanic@yahoo.com.au"
USER_PASSWORD = "Andmay123"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def user_session():
    return _login(USER_EMAIL, USER_PASSWORD)


# --- /api/auth/me smoke -----------------------------------------------------
class TestAuthMeSmoke:
    def test_admin_me(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("email") == ADMIN_EMAIL
        assert body.get("role") == "admin"

    def test_user_me(self, user_session):
        r = user_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("email") == USER_EMAIL


# --- /api/admin/ads CRUD + RBAC smoke ---------------------------------------
class TestAdminAdsSmoke:
    def test_admin_creates_ad(self, admin_session):
        payload = {
            "name": "TEST_iter14_smoke_ad",
            "click_url": "https://example.com",
            "image_url": "https://example.com/img.png",
            "active": True,
        }
        r = admin_session.post(f"{BASE_URL}/api/admin/ads", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        ad = r.json()
        assert ad.get("name") == payload["name"]
        ad_id = ad.get("id")
        assert isinstance(ad_id, str) and len(ad_id) > 0
        # cleanup
        d = admin_session.delete(f"{BASE_URL}/api/admin/ads/{ad_id}", timeout=15)
        assert d.status_code in (200, 204)

    def test_non_admin_cannot_create(self, user_session):
        r = user_session.post(
            f"{BASE_URL}/api/admin/ads",
            json={"name": "TEST_iter14_nope", "click_url": "https://x.com", "image_url": "https://x.com/i.png"},
            timeout=15,
        )
        assert r.status_code == 403


# --- /api/admin/ads/analytics smoke -----------------------------------------
class TestAdsAnalyticsSmoke:
    def test_admin_analytics_default(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ads/analytics?days=7", timeout=15)
        assert r.status_code == 200
        body = r.json()
        # Either {totals,ads} or list — verify shape lightly
        assert isinstance(body, dict)
        assert "totals" in body or "ads" in body

    def test_admin_analytics_invalid_days(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ads/analytics?days=0", timeout=15)
        assert r.status_code in (400, 422)

    def test_ad_manager_can_access_analytics(self, admin_session):
        # Find davidjovanic's user_id, promote, hit analytics, then revoke
        users = admin_session.get(f"{BASE_URL}/api/admin/users", timeout=15)
        if users.status_code != 200:
            pytest.skip("admin/users not available")
        target = next((u for u in users.json() if u.get("email") == USER_EMAIL), None)
        if not target:
            pytest.skip("test user not present")
        uid = target.get("id") or target.get("_id")
        grant = admin_session.post(f"{BASE_URL}/api/admin/ad-managers", json={"user_id": uid}, timeout=15)
        assert grant.status_code in (200, 201), grant.text
        try:
            mgr = _login(USER_EMAIL, USER_PASSWORD)
            r = mgr.get(f"{BASE_URL}/api/admin/ads/analytics?days=7", timeout=15)
            assert r.status_code == 200
        finally:
            admin_session.delete(f"{BASE_URL}/api/admin/ad-managers/{uid}", timeout=15)


# --- /api/health/time smoke -------------------------------------------------
class TestHealthTime:
    def test_health_time(self):
        r = requests.get(f"{BASE_URL}/api/health/time", timeout=15)
        assert r.status_code == 200
        body = r.json()
        # Existing iter10 shape uses 'server_time' or similar; just confirm 200 + JSON dict
        assert isinstance(body, dict)


# --- Frontend index.html SEO meta tags --------------------------------------
class TestSEOMeta:
    def test_index_has_seo_meta(self):
        r = requests.get(BASE_URL + "/", timeout=15)
        assert r.status_code == 200
        html = r.text
        # description
        assert re.search(r'<meta\s+name="description"\s+content="GoMofos', html, re.I), \
            "meta description missing or content changed"
        # og: tags
        assert 'property="og:title"' in html
        assert 'property="og:description"' in html
        assert 'property="og:image"' in html
        # twitter card
        assert 'name="twitter:card"' in html
