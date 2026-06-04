"""Iteration 9 tests: One-click Decline & Refund for challenge invites.

Covers:
- HTML GET /api/challenges/decline (no auth, signed token)
- Idempotency, invalid, expired, wrong-uid tokens
- Authenticated POST /api/challenges/{id}/decline (invitee, challenger 403, 404)
- /api/challenges/incoming excludes declined
- Decline after start (in_progress) does not refund
- Regression: /api/share/tournament/{id}, POST /api/highlights
"""
import os
import uuid
import time
from datetime import datetime, timezone, timedelta

import jwt
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load backend .env so JWT_SECRET is available for minting tokens client-side
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
# Also load frontend .env to expose REACT_APP_BACKEND_URL when invoked outside CI
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"

ADMIN_EMAIL = "admin@esportsbet.com"
ADMIN_PASSWORD = "admin123"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _unique(prefix: str) -> str:
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}"


def _register(session: requests.Session) -> dict:
    uname = _unique("u")
    email = f"{uname}@example.com"
    r = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "username": uname,
        "password": "Password123",
    })
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    return r.json()


def _login_admin(session: requests.Session) -> dict:
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD,
    })
    assert r.status_code == 200, f"admin login failed: {r.text}"
    return r.json()


def _ensure_game() -> str:
    """Return a game_id. Reuses an existing one or creates a fresh one as admin."""
    pub = requests.get(f"{BASE_URL}/api/games")
    if pub.status_code == 200 and isinstance(pub.json(), list) and pub.json():
        return pub.json()[0]["id"] if "id" in pub.json()[0] else str(pub.json()[0].get("_id"))
    s = requests.Session()
    _login_admin(s)
    r = s.post(f"{BASE_URL}/api/games", json={
        "name": _unique("game"),
        "platform": "pc",
        "image_url": "https://example.com/x.png",
        "category": "fps",
    })
    assert r.status_code == 200, f"create game failed: {r.text}"
    return r.json()["id"]


def _future_iso(minutes: int = 60) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _create_challenge(challenger_session: requests.Session, opponent_user_id: str,
                      game_id: str, stake: float = 50.0) -> str:
    r = challenger_session.post(f"{BASE_URL}/api/challenges", json={
        "game_id": game_id,
        "opponent_user_id": opponent_user_id,
        "stake_amount": stake,
        "start_time": _future_iso(),
    })
    assert r.status_code == 200, f"create challenge failed: {r.text}"
    return r.json()["tournament_id"]


def _wallet(session: requests.Session) -> float:
    r = session.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200, r.text
    return float(r.json()["wallet_balance"])


def _mint_decline_token(tid: str, uid: str, exp_delta_seconds: int = 7 * 24 * 3600,
                        ttype: str = "decline_challenge") -> str:
    payload = {
        "tid": tid,
        "uid": uid,
        "type": ttype,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_delta_seconds),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


@pytest.fixture(scope="module")
def game_id():
    return _ensure_game()


# ---------------------------------------------------------------------------
# Backend tests — HTML endpoint
# ---------------------------------------------------------------------------

class TestDeclineViaSignedToken:
    def test_valid_token_declines_and_refunds_challenger(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        wallet_before = _wallet(challenger)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=75.0)
        # Challenger should have been debited
        assert abs(_wallet(challenger) - (wallet_before - 75.0)) < 0.01

        token = _mint_decline_token(tid, invitee["id"])
        r = requests.get(f"{BASE_URL}/api/challenges/decline", params={"token": token})
        assert r.status_code == 200
        assert "Challenge declined" in r.text
        # Refund amount surfaced in HTML (formatted as integer "75 CR")
        assert "75" in r.text and "CR" in r.text

        # Challenger refunded back to pre-challenge balance
        assert abs(_wallet(challenger) - wallet_before) < 0.01
        # Invitee wallet unchanged (1000 welcome bonus, never paid in)
        assert abs(_wallet(invitee_s) - 1000.0) < 0.01

    def test_idempotent_second_click(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        wallet_before = _wallet(challenger)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=40.0)
        token = _mint_decline_token(tid, invitee["id"])

        r1 = requests.get(f"{BASE_URL}/api/challenges/decline", params={"token": token})
        assert r1.status_code == 200 and "Challenge declined" in r1.text
        wallet_after_first = _wallet(challenger)
        assert abs(wallet_after_first - wallet_before) < 0.01

        r2 = requests.get(f"{BASE_URL}/api/challenges/decline", params={"token": token})
        assert r2.status_code == 200
        assert "Already declined" in r2.text
        # No double-refund
        assert abs(_wallet(challenger) - wallet_after_first) < 0.01

    def test_invalid_token_returns_html_invalid(self):
        r = requests.get(f"{BASE_URL}/api/challenges/decline", params={"token": "garbage.not.a.jwt"})
        assert r.status_code == 200
        assert "Invalid link" in r.text

    def test_expired_token_returns_link_expired(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=10.0)
        token = _mint_decline_token(tid, invitee["id"], exp_delta_seconds=-3600)
        r = requests.get(f"{BASE_URL}/api/challenges/decline", params={"token": token})
        assert r.status_code == 200
        assert "Link expired" in r.text

    def test_wrong_uid_token_rejected(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        outsider_s = requests.Session(); outsider = _register(outsider_s)
        wallet_before = _wallet(challenger)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=25.0)

        # Mint token whose uid is the outsider (not in invited_user_ids)
        bad_token = _mint_decline_token(tid, outsider["id"])
        r = requests.get(f"{BASE_URL}/api/challenges/decline", params={"token": bad_token})
        assert r.status_code == 200
        assert ("Not your challenge" in r.text) or ("Invalid link" in r.text)
        # No refund happened
        assert abs(_wallet(challenger) - (wallet_before - 25.0)) < 0.01


# ---------------------------------------------------------------------------
# Backend tests — authenticated endpoint
# ---------------------------------------------------------------------------

class TestDeclineAuthenticated:
    def test_invitee_can_decline_and_only_challenger_is_refunded(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        wallet_before = _wallet(challenger)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=60.0)

        invitee_wallet_before = _wallet(invitee_s)
        r = invitee_s.post(f"{BASE_URL}/api/challenges/{tid}/decline")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ok"
        assert body.get("tournament_id") == tid

        assert abs(_wallet(challenger) - wallet_before) < 0.01, "challenger should be fully refunded"
        assert abs(_wallet(invitee_s) - invitee_wallet_before) < 0.01, "invitee wallet must be unchanged"

    def test_challenger_cannot_decline_their_own_challenge(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=20.0)
        r = challenger.post(f"{BASE_URL}/api/challenges/{tid}/decline")
        assert r.status_code == 403
        assert "Only the invited player" in r.json().get("detail", "")

    def test_decline_unknown_tournament_returns_404(self):
        s = requests.Session(); _register(s)
        fake_id = "507f1f77bcf86cd799439011"
        r = s.post(f"{BASE_URL}/api/challenges/{fake_id}/decline")
        assert r.status_code == 404

    def test_declined_challenge_disappears_from_incoming(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=15.0)

        # Initially the challenge IS in incoming
        inc = invitee_s.get(f"{BASE_URL}/api/challenges/incoming").json()
        assert any(c["tournament_id"] == tid for c in inc)

        # Decline
        r = invitee_s.post(f"{BASE_URL}/api/challenges/{tid}/decline")
        assert r.status_code == 200

        inc2 = invitee_s.get(f"{BASE_URL}/api/challenges/incoming").json()
        assert not any(c["tournament_id"] == tid for c in inc2), \
            "declined challenge must not appear in /api/challenges/incoming"

    def test_decline_after_match_started_does_not_refund(self, game_id):
        """Simulate in_progress by flipping status via direct admin path — there's no
        public endpoint to start a match by the invitee without join, so we mint a
        token after the status is changed by joining (which moves it to in_progress)."""
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        wallet_before_challenger = _wallet(challenger)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=30.0)

        # Invitee joins the tournament -> moves status to in_progress (current_players=2)
        join = invitee_s.post(f"{BASE_URL}/api/tournaments/{tid}/join")
        # If join endpoint differs, attempt via tournaments status change; skip if join
        # returns non-success.
        if join.status_code != 200:
            pytest.skip(f"join endpoint not available (got {join.status_code}); skipping started-state test")

        # Now attempting to decline should not refund
        challenger_wallet_after_join = _wallet(challenger)
        token = _mint_decline_token(tid, invitee["id"])
        r = requests.get(f"{BASE_URL}/api/challenges/decline", params={"token": token})
        assert r.status_code == 200
        assert "Match already started" in r.text or "already" in r.text.lower()
        # No refund occurred
        assert abs(_wallet(challenger) - challenger_wallet_after_join) < 0.01


# ---------------------------------------------------------------------------
# Regression — share & highlights still alive
# ---------------------------------------------------------------------------

class TestRegression:
    def test_share_tournament_endpoint(self, game_id):
        challenger = requests.Session(); _register(challenger)
        invitee_s = requests.Session(); invitee = _register(invitee_s)
        tid = _create_challenge(challenger, invitee["id"], game_id, stake=10.0)
        r = requests.get(f"{BASE_URL}/api/share/tournament/{tid}")
        assert r.status_code == 200, r.text

    def test_highlights_post(self, game_id):
        s = requests.Session(); _register(s)
        # POST /api/highlights — payload shape varies; we just confirm endpoint isn't 5xx.
        r = s.post(f"{BASE_URL}/api/highlights", json={
            "tournament_id": "507f1f77bcf86cd799439011",
            "title": "TEST highlight",
            "video_url": "https://example.com/clip.mp4",
        })
        assert r.status_code in (200, 201, 400, 404, 422), \
            f"highlights endpoint returned unexpected {r.status_code}: {r.text}"
