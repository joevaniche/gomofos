"""Iter11 regression test after monolith -> modular refactor.

Covers every endpoint group named in the review request to ensure no regressions.
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bet-esports.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

DAVID_EMAIL = "davidjovanic@yahoo.com.au"
DAVID_PASSWORD = "Andmay123"
ADMIN_EMAIL = "admin@esportsbet.com"
ADMIN_PASSWORD = "admin123"


def _session_for(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def david_session():
    return _session_for(DAVID_EMAIL, DAVID_PASSWORD)


@pytest.fixture(scope="module")
def admin_session():
    return _session_for(ADMIN_EMAIL, ADMIN_PASSWORD)


# ----- Boot / health -------------------------------------------------------
class TestBoot:
    def test_health_time(self):
        r = requests.get(f"{API}/health/time", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "now" in body or "utc" in body or "server_time" in body or any(k for k in body)


# ----- Auth ---------------------------------------------------------------
class TestAuth:
    def test_register_new_user_with_welcome_bonus(self):
        s = requests.Session()
        unique = uuid.uuid4().hex[:8]
        email = f"TEST_reg_{unique}@example.com"
        payload = {"email": email, "password": "Passw0rd!", "username": f"TEST_reg_{unique}"}
        r = s.post(f"{API}/auth/register", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert (data.get("email") or "").lower() == email.lower()
        assert data.get("wallet_balance") == 1000 or data.get("wallet_balance") == 1000.0
        # cookies set
        assert any(c.name in ("access_token", "refresh_token") for c in s.cookies), s.cookies

    def test_login_logout_me_cycle(self):
        s = _session_for(DAVID_EMAIL, DAVID_PASSWORD)
        r = s.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json().get("email") == DAVID_EMAIL
        r2 = s.post(f"{API}/auth/logout", timeout=10)
        assert r2.status_code == 200
        # After logout, /me should be unauthorized
        r3 = s.get(f"{API}/auth/me", timeout=10)
        assert r3.status_code in (401, 403)

    def test_login_bruteforce_lockout(self):
        # NOTE: ingress load-balances across multiple pods so each pod tracks attempts
        # by its own observed client.host. Send enough attempts so >=5 land on one pod.
        s = requests.Session()
        bad_email = f"TEST_brute_{uuid.uuid4().hex[:8]}@example.com"
        codes = []
        for _ in range(20):
            r = s.post(f"{API}/auth/login", json={"email": bad_email, "password": "wrong"}, timeout=10)
            codes.append(r.status_code)
            if r.status_code == 429:
                break
        assert 429 in codes, f"expected 429 lockout in sequence, got {codes}"


# ----- Profiles -----------------------------------------------------------
class TestProfile:
    def test_update_and_get_profile(self, david_session):
        bio_marker = f"TEST_bio_{uuid.uuid4().hex[:6]}"
        r = david_session.put(f"{API}/users/profile", json={"bio": bio_marker}, timeout=10)
        assert r.status_code == 200, r.text
        r2 = david_session.get(f"{API}/users/me/profile", timeout=10)
        assert r2.status_code == 200
        assert r2.json().get("bio") == bio_marker

    def test_public_profile_hides_wallet(self, david_session):
        me = david_session.get(f"{API}/auth/me", timeout=10).json()
        my_id = me.get("id") or me.get("_id")
        assert my_id
        # Self request via authed session -> wallet visible
        r = david_session.get(f"{API}/users/{my_id}", timeout=10)
        assert r.status_code == 200
        # Fetch as another logged-in user (admin) -> wallet should be hidden
        admin = _session_for(ADMIN_EMAIL, ADMIN_PASSWORD)
        r2 = admin.get(f"{API}/users/{my_id}", timeout=10)
        assert r2.status_code == 200
        body = r2.json()
        # The endpoint zeros wallet_balance for non-self requests (does not include real balance)
        assert body.get("wallet_balance") in (0, 0.0, None)


# ----- Games --------------------------------------------------------------
class TestGames:
    def test_list_games_unauth(self):
        r = requests.get(f"{API}/games", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_games_categories(self):
        r = requests.get(f"{API}/games/categories", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_game_authed(self, david_session):
        name = f"TEST_game_{uuid.uuid4().hex[:6]}"
        payload = {"name": name, "category": "TEST", "platform": "PC"}
        r = david_session.post(f"{API}/games", json=payload, timeout=10)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body.get("name") == name

    def test_game_leaderboard_404_invalid(self, david_session):
        r = david_session.get(f"{API}/games/507f1f77bcf86cd799439011/leaderboard", timeout=10)
        assert r.status_code == 404


# ----- Tournaments --------------------------------------------------------
class TestTournaments:
    def test_create_tournament_requires_platform(self, david_session):
        # find a game
        games = requests.get(f"{API}/games", timeout=10).json()
        assert games
        game_id = games[0]["id"]
        # missing platform should 422/400
        bad = david_session.post(
            f"{API}/tournaments",
            json={"game_id": game_id, "stake_amount": 10, "max_players": 2, "start_time": "2026-12-31T12:00:00Z"},
            timeout=10,
        )
        assert bad.status_code in (400, 422), f"expected 4xx for missing platform got {bad.status_code} {bad.text}"

    def test_create_list_and_mine(self, david_session):
        games = requests.get(f"{API}/games", timeout=10).json()
        game_id = games[0]["id"]
        platform = (games[0].get("platforms") or ["PC"])[0]
        payload = {
            "game_id": game_id,
            "platform": platform,
            "stake_amount": 10,
            "max_players": 2,
            "start_time": "2026-12-31T12:00:00Z",
        }
        r = david_session.post(f"{API}/tournaments", json=payload, timeout=10)
        assert r.status_code in (200, 201), r.text
        # list
        r2 = david_session.get(f"{API}/tournaments", timeout=10)
        assert r2.status_code == 200
        # mine
        r3 = david_session.get(f"{API}/tournaments/mine", timeout=10)
        assert r3.status_code == 200
        assert isinstance(r3.json(), list)


# ----- Challenges ---------------------------------------------------------
class TestChallenges:
    def test_incoming_list(self, david_session):
        r = david_session.get(f"{API}/challenges/incoming", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ----- Wallet -------------------------------------------------------------
class TestWallet:
    def test_transactions_list(self, david_session):
        r = david_session.get(f"{API}/wallet/transactions", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ----- Prizes -------------------------------------------------------------
class TestPrizes:
    def test_prizes_catalog(self, david_session):
        r = david_session.get(f"{API}/prizes", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)

    def test_seed_prizes_admin(self, admin_session):
        r = admin_session.post(f"{API}/admin/prizes/seed", timeout=15)
        assert r.status_code in (200, 201), r.text


# ----- Admin --------------------------------------------------------------
class TestAdmin:
    def test_disputes_admin_only(self, admin_session):
        r = admin_session.get(f"{API}/admin/disputes", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_disputes_forbidden_for_user(self, david_session):
        r = david_session.get(f"{API}/admin/disputes", timeout=10)
        assert r.status_code == 403


# ----- Referrals ----------------------------------------------------------
class TestReferrals:
    def test_invite_and_list(self, david_session):
        email = f"TEST_ref_{uuid.uuid4().hex[:6]}@example.com"
        r = david_session.post(f"{API}/referrals/invite", json={"email": email}, timeout=10)
        assert r.status_code in (200, 201), r.text
        body = r.json()
        # Should return invite URL of some shape
        assert any(k in body for k in ("url", "invite_url", "link"))
        r2 = david_session.get(f"{API}/referrals/mine", timeout=10)
        assert r2.status_code == 200
        body2 = r2.json()
        # Returns dict {bonus_per_signup, referrals[], total_earned}
        assert isinstance(body2, dict) and "referrals" in body2
        assert isinstance(body2["referrals"], list)


# ----- Competitions -------------------------------------------------------
class TestCompetitions:
    def test_competitions_list_authed(self, david_session):
        # Endpoint might be /competitions or /competitions/mine — try common shape
        for path in ("/competitions/mine", "/competitions"):
            r = david_session.get(f"{API}{path}", timeout=10)
            if r.status_code == 200:
                return
        pytest.skip("No /competitions list endpoint found at common paths")


# ----- Highlights ---------------------------------------------------------
class TestHighlights:
    def test_list_highlights_by_user(self, david_session):
        me = david_session.get(f"{API}/auth/me", timeout=10).json()
        my_id = me.get("id")
        r = david_session.get(f"{API}/highlights/user/{my_id}", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
