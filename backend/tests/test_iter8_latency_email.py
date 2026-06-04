"""Iteration 8 tests: SendGrid graceful failure + latency-advantage tie-breaker.

Auth model: cookie-based session (POST /api/auth/login or /api/auth/register sets
httpOnly cookies). All API calls use requests.Session so cookies are preserved.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://esports-bet-3.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Load backend/.env so the in-process SendGrid test sees credentials
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv  # noqa: E402
load_dotenv("/app/backend/.env")


# ---------- helpers ----------
def _register(prefix: str) -> dict:
    s = requests.Session()
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{prefix}_{suffix}@example.com"
    username = f"TEST{prefix}{suffix}"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": "Password123", "username": username}, timeout=15)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    me = s.get(f"{API}/auth/me", timeout=15).json()
    return {"s": s, "id": me.get("id"), "email": email, "username": username}


def _admin_session() -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@esportsbet.com", "password": "admin123"}, timeout=15)
    assert r.status_code == 200, r.text
    return s


def _first_game_id() -> str:
    r = requests.get(f"{API}/games", timeout=15)
    assert r.status_code == 200, r.text
    games = r.json()
    assert games
    return games[0]["id"]


def _create_open_tournament(creator_session: requests.Session, game_id: str, stake: int = 20) -> str:
    start_time = "2026-12-31T00:00:00Z"
    r = creator_session.post(
        f"{API}/tournaments",
        json={
            "game_id": game_id,
            "stake_amount": stake,
            "max_players": 2,
            "title": f"TEST_iter8_{uuid.uuid4().hex[:6]}",
            "start_time": start_time,
        },
        timeout=15,
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    return data.get("tournament_id") or data.get("id")


def _seed_latency(session: requests.Session, tid: str, values: list):
    for v in values:
        r = session.post(f"{API}/tournaments/{tid}/latency", params={"latency_ms": v}, timeout=15)
        assert r.status_code == 200, r.text


# ---------- 1. email_service swallows SendGrid 403 ----------
def test_email_service_swallows_sendgrid_403():
    from email_service import send_email_async
    asyncio.run(send_email_async(to="helpdesk@gomofos.com", subject="t", html="x", plain="x"))


# ---------- 2. Constants ----------
def test_latency_constants_exist():
    with open("/app/backend/server.py", "r") as f:
        src = f.read()
    assert "LATENCY_WARN_MS = 100" in src
    assert "LATENCY_HIGH_MS = 200" in src


# ---------- 3. POST /api/challenges works + non-blocking ----------
def test_challenge_endpoint_creates_tournament_non_blocking():
    a = _register("chgA")
    b = _register("chgB")
    game_id = _first_game_id()

    t0 = time.time()
    r = a["s"].post(
        f"{API}/challenges",
        json={"opponent_user_id": b["id"], "stake_amount": 50, "game_id": game_id, "start_time": "2026-12-31T00:00:00Z"},
        timeout=15,
    )
    elapsed = time.time() - t0
    assert r.status_code == 200, r.text
    data = r.json()
    assert "tournament_id" in data and data["tournament_id"]
    assert elapsed < 8.0, f"challenge endpoint too slow ({elapsed:.2f}s)"


# ---------- shared fixture: 2-player in_progress tournament ----------
@pytest.fixture(scope="module")
def two_player_ctx():
    a = _register("twpA")
    b = _register("twpB")
    game_id = _first_game_id()
    tid = _create_open_tournament(a["s"], game_id)
    rj = b["s"].post(f"{API}/tournaments/{tid}/join", timeout=15)
    assert rj.status_code == 200, rj.text
    return {"a": a, "b": b, "tid": tid}


# ---------- 4. POST /latency participant-only ----------
def test_latency_post_participant_only(two_player_ctx):
    tid = two_player_ctx["tid"]
    r = two_player_ctx["a"]["s"].post(f"{API}/tournaments/{tid}/latency", params={"latency_ms": 42}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("recorded") is True

    stranger = _register("strange")
    r2 = stranger["s"].post(f"{API}/tournaments/{tid}/latency", params={"latency_ms": 50}, timeout=15)
    assert r2.status_code == 403, r2.text


# ---------- 5. latency-advantage scenarios ----------
def test_latency_advantage_progression():
    a = _register("advA")
    b = _register("advB")
    game_id = _first_game_id()
    tid = _create_open_tournament(a["s"], game_id)
    b["s"].post(f"{API}/tournaments/{tid}/join", timeout=15)

    # (a) 0 samples
    r = a["s"].get(f"{API}/tournaments/{tid}/latency-advantage", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["advantage_user_id"] is None
    assert data["breakdown"] == []
    assert data["policy"] == "lower_avg_ms_wins_ties"

    # (b) Only one user has 3+ samples
    _seed_latency(a["s"], tid, [30, 40, 35])
    data = a["s"].get(f"{API}/tournaments/{tid}/latency-advantage", timeout=15).json()
    assert data["advantage_user_id"] is None, data
    assert len(data["breakdown"]) == 1

    # (c) Both have 3+ samples, B is higher avg → A wins
    _seed_latency(b["s"], tid, [60, 70, 65])
    data = a["s"].get(f"{API}/tournaments/{tid}/latency-advantage", timeout=15).json()
    assert data["advantage_user_id"] == a["id"], data

    # (d) Add high samples to A → status='high' on A, so B wins despite higher avg
    _seed_latency(a["s"], tid, [250, 260, 240])
    data = a["s"].get(f"{API}/tournaments/{tid}/latency-advantage", timeout=15).json()
    by_uid = {x["user_id"]: x for x in data["breakdown"]}
    assert by_uid[a["id"]]["status"] == "high"
    assert data["advantage_user_id"] == b["id"], data


# ---------- 6. latency-advantage auth/role ----------
def test_latency_advantage_requires_auth(two_player_ctx):
    tid = two_player_ctx["tid"]
    # No auth (fresh session, no cookie)
    fresh = requests.Session()
    r = fresh.get(f"{API}/tournaments/{tid}/latency-advantage", timeout=15)
    assert r.status_code in (401, 403), r.text

    stranger = _register("strange3")
    r2 = stranger["s"].get(f"{API}/tournaments/{tid}/latency-advantage", timeout=15)
    assert r2.status_code == 403, r2.text

    admin = _admin_session()
    r3 = admin.get(f"{API}/tournaments/{tid}/latency-advantage", timeout=15)
    assert r3.status_code == 200, r3.text


# ---------- 7. Dispute populates latency_advantage ----------
def test_dispute_flow_populates_latency_advantage():
    a = _register("dispA")
    b = _register("dispB")
    game_id = _first_game_id()
    tid = _create_open_tournament(a["s"], game_id)
    b["s"].post(f"{API}/tournaments/{tid}/join", timeout=15)

    # A high, B low
    _seed_latency(a["s"], tid, [220, 230, 210])
    _seed_latency(b["s"], tid, [40, 50, 45])

    r1 = a["s"].post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": a["id"]}, timeout=15)
    assert r1.status_code == 200, r1.text
    r2 = b["s"].post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": b["id"]}, timeout=15)
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["status"] == "disputed", data
    assert "latency_advantage" in data
    la = data["latency_advantage"]
    assert la and la["advantage_user_id"] == b["id"], la

    # GET detail
    r3 = a["s"].get(f"{API}/tournaments/{tid}", timeout=15)
    assert r3.status_code == 200
    detail = r3.json()
    assert "latency_advantage" in detail
    assert detail["latency_advantage"]["advantage_user_id"] == b["id"]
    assert detail["status"] == "disputed"


# ---------- 8. detail field present before dispute ----------
def test_tournament_detail_exposes_latency_advantage_field(two_player_ctx):
    tid = two_player_ctx["tid"]
    r = two_player_ctx["a"]["s"].get(f"{API}/tournaments/{tid}", timeout=15)
    assert r.status_code == 200
    detail = r.json()
    assert "latency_advantage" in detail  # may be None pre-dispute


# ---------- 9. Evidence upload regression ----------
def test_evidence_upload_regression():
    a = _register("evA")
    b = _register("evB")
    game_id = _first_game_id()
    tid = _create_open_tournament(a["s"], game_id)
    b["s"].post(f"{API}/tournaments/{tid}/join", timeout=15)
    a["s"].post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": a["id"]}, timeout=15)
    b["s"].post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": b["id"]}, timeout=15)

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
        b"\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    files = {"file": ("evidence.png", png_bytes, "image/png")}
    r = a["s"].post(f"{API}/tournaments/{tid}/evidence", files=files, timeout=20)
    assert r.status_code in (200, 201), r.text
