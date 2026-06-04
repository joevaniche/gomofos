"""Backend tests for Highlight Reels + Tournament Share Card (iteration_7)."""
import os
import time
import io
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://esports-bet-3.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@esportsbet.com"
ADMIN_PASSWORD = "admin123"


# ---------- helpers ----------
def _register(email, password="Password123", username=None):
    s = requests.Session()
    username = username or f"u{int(time.time()*1000)%10**9}"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": password, "username": username})
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    return s, r.json()


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    me = s.get(f"{API}/auth/me")
    return s, me.json()


def _mp4_bytes(size=1024):
    # tiny synthetic mp4-ish blob: ftyp box + filler
    header = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    return header + b"\x00" * max(0, size - len(header))


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    s, me = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
    return s, me


@pytest.fixture(scope="module")
def user_session():
    ts = int(time.time())
    s, _ = _register(f"testuser_hl_{ts}@example.com", username=f"hluser{ts}")
    me = s.get(f"{API}/auth/me").json()
    return s, me


@pytest.fixture(scope="module")
def second_user_session():
    ts = int(time.time()) + 1
    s, _ = _register(f"testuser_hl2_{ts}@example.com", username=f"hluser2{ts}")
    me = s.get(f"{API}/auth/me").json()
    return s, me


# =================== HIGHLIGHTS ===================
class TestHighlightUpload:
    def test_upload_valid_mp4(self, user_session):
        s, me = user_session
        files = {"file": ("clip.mp4", _mp4_bytes(2048), "video/mp4")}
        data = {"title": "TEST_clip_one", "duration_sec": "12.5"}
        r = s.post(f"{API}/highlights", files=files, data=data)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("id", "title", "video_url", "duration_sec", "view_count", "created_at"):
            assert k in body, f"missing {k}"
        assert body["title"] == "TEST_clip_one"
        assert body["view_count"] == 0
        assert body["video_url"].startswith("/api/highlights/")
        pytest.reel_id = body["id"]

    def test_list_user_highlights(self, user_session):
        s, me = user_session
        r = s.get(f"{API}/highlights/user/{me['id']}")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1
        assert any(it["id"] == pytest.reel_id for it in items)
        # newest first
        if len(items) >= 2:
            assert items[0]["created_at"] >= items[1]["created_at"]

    def test_get_highlight_increments_view(self, user_session):
        r1 = requests.get(f"{API}/highlights/{pytest.reel_id}")
        assert r1.status_code == 200
        v1 = r1.json()["view_count"]
        r2 = requests.get(f"{API}/highlights/{pytest.reel_id}")
        v2 = r2.json()["view_count"]
        assert v2 == v1 + 1, f"view count not incremented: {v1} -> {v2}"

    def test_stream_returns_video_bytes(self):
        r = requests.get(f"{API}/highlights/{pytest.reel_id}/stream")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert ct.startswith("video/"), f"unexpected content-type {ct}"
        assert len(r.content) > 0

    def test_reject_non_video_content_type(self, user_session):
        s, _ = user_session
        files = {"file": ("img.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
        data = {"title": "TEST_bad"}
        r = s.post(f"{API}/highlights", files=files, data=data)
        assert r.status_code == 400, r.text

    def test_reject_empty_title(self, user_session):
        s, _ = user_session
        files = {"file": ("clip.mp4", _mp4_bytes(512), "video/mp4")}
        data = {"title": "   "}
        r = s.post(f"{API}/highlights", files=files, data=data)
        assert r.status_code == 400, r.text

    def test_reject_oversize_file(self, user_session):
        s, _ = user_session
        big = _mp4_bytes(51 * 1024 * 1024)  # 51 MB
        files = {"file": ("huge.mp4", big, "video/mp4")}
        data = {"title": "TEST_huge"}
        r = s.post(f"{API}/highlights", files=files, data=data)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"
        assert "large" in r.text.lower() or "size" in r.text.lower()


class TestHighlightDelete:
    def test_owner_can_delete(self, user_session, second_user_session):
        s, _ = user_session
        # upload a fresh reel to delete
        files = {"file": ("clip2.mp4", _mp4_bytes(512), "video/mp4")}
        r = s.post(f"{API}/highlights", files=files, data={"title": "TEST_delete_me"})
        assert r.status_code == 200
        rid = r.json()["id"]

        # other user cannot delete
        s2, _ = second_user_session
        r2 = s2.delete(f"{API}/highlights/{rid}")
        assert r2.status_code == 403, f"non-owner delete: {r2.status_code} {r2.text}"

        # owner can delete
        r3 = s.delete(f"{API}/highlights/{rid}")
        assert r3.status_code == 200
        # now gone
        r4 = requests.get(f"{API}/highlights/{rid}")
        assert r4.status_code == 404


# =================== SHARE CARD ===================
class TestShareCard:
    def _get_a_tournament_id(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/tournaments")
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list) and len(items) > 0, "no tournaments seeded"
        return items[0]["id"]

    def test_share_card_meta_tags(self, admin_session):
        tid = self._get_a_tournament_id(admin_session)
        r = requests.get(f"{API}/share/tournament/{tid}")
        assert r.status_code == 200, r.text
        html = r.text
        for tag in ['og:title', 'og:description', 'og:url', 'og:image', 'twitter:card']:
            assert tag in html, f"missing {tag} in share card"

    def test_share_card_with_reel_adds_video_meta(self, admin_session, user_session):
        tid = self._get_a_tournament_id(admin_session)
        rid = pytest.reel_id
        r = requests.get(f"{API}/share/tournament/{tid}?reel={rid}")
        assert r.status_code == 200
        html = r.text
        for tag in ['og:video', 'og:video:secure_url', 'og:video:type', 'twitter:player']:
            assert tag in html, f"missing {tag} when reel attached"
        assert f"/api/highlights/{rid}/stream" in html

    def test_share_card_invalid_tournament_404(self):
        r = requests.get(f"{API}/share/tournament/000000000000000000000000")
        assert r.status_code == 404
        assert "not found" in r.text.lower()


# =================== REGRESSION: evidence upload ===================
class TestEvidenceRegression:
    def test_evidence_upload_image_still_works(self, admin_session):
        s, _ = admin_session
        r = s.get(f"{API}/tournaments")
        assert r.status_code == 200
        tlist = r.json()
        if not tlist:
            pytest.skip("no tournaments available")
        # find one admin participates in or just attempt; endpoint may require participation
        tid = tlist[0]["id"]
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        files = {"file": ("evid.png", png, "image/png")}
        r = s.post(f"{API}/tournaments/{tid}/evidence", files=files)
        # 200 if admin is a participant; otherwise 4xx but NOT 500
        assert r.status_code < 500, f"evidence endpoint server error: {r.status_code} {r.text[:200]}"
