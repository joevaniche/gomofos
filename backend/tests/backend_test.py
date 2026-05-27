import os, time, requests, pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://esports-bet-3.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

@pytest.fixture(scope="module")
def s1():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"}); return s

@pytest.fixture(scope="module")
def s2():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"}); return s

@pytest.fixture(scope="module")
def users(s1, s2):
    t = int(time.time())
    u1 = {"email": f"TEST_u1_{t}@e.com", "password": "Passw0rd!", "username": f"TEST_u1_{t}"}
    u2 = {"email": f"TEST_u2_{t}@e.com", "password": "Passw0rd!", "username": f"TEST_u2_{t}"}
    r1 = s1.post(f"{API}/auth/register", json=u1); assert r1.status_code == 200, r1.text
    r2 = s2.post(f"{API}/auth/register", json=u2); assert r2.status_code == 200, r2.text
    return {"u1": r1.json(), "u2": r2.json()}

def test_register_and_me(s1, users):
    r = s1.get(f"{API}/auth/me"); assert r.status_code == 200
    assert r.json()["email"] == users["u1"]["email"]

def test_login_invalid():
    r = requests.post(f"{API}/auth/login", json={"email": "nouser@x.com", "password": "x"})
    assert r.status_code == 401

def test_login_admin():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@esportsbet.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.cookies

def test_create_game_and_list(s1):
    r = s1.post(f"{API}/games", json={"name": "TEST_FIFA24", "platform": "PS5"})
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    r2 = s1.get(f"{API}/games"); assert r2.status_code == 200
    assert any(g["id"] == gid for g in r2.json())
    pytest.game_id = gid

def test_create_tournament_insufficient(s1):
    r = s1.post(f"{API}/tournaments", json={"game_id": pytest.game_id, "stake_amount": 100, "max_players": 4, "start_time": "2026-12-31T10:00:00Z"})
    assert r.status_code == 400  # no wallet balance

def test_seed_wallet_and_create_tournament(s1, users):
    # Directly credit wallet via DB? We don't have admin endpoint. Skip stake by using 0.
    r = s1.post(f"{API}/tournaments", json={"game_id": pytest.game_id, "stake_amount": 0, "max_players": 4, "start_time": "2026-12-31T10:00:00Z"})
    assert r.status_code == 200, r.text
    pytest.tournament_id = r.json()["id"]

def test_list_tournaments(s1):
    r = s1.get(f"{API}/tournaments"); assert r.status_code == 200
    assert any(t["id"] == pytest.tournament_id for t in r.json())

def test_join_tournament(s2):
    r = s2.post(f"{API}/tournaments/{pytest.tournament_id}/join")
    assert r.status_code == 200, r.text

def test_tournament_details(s1):
    r = s1.get(f"{API}/tournaments/{pytest.tournament_id}")
    assert r.status_code == 200
    assert r.json()["current_players"] == 2

def test_chat(s1, s2):
    r = s1.post(f"{API}/chat", json={"tournament_id": pytest.tournament_id, "message": "hi"})
    assert r.status_code == 200
    r2 = s2.post(f"{API}/chat", json={"tournament_id": pytest.tournament_id, "message": "yo"})
    assert r2.status_code == 200
    g = s1.get(f"{API}/chat/{pytest.tournament_id}")
    assert g.status_code == 200 and len(g.json()) >= 2

def test_complete_tournament(s1, s2, users):
    r = s1.post(f"{API}/tournaments/{pytest.tournament_id}/complete", params={"winner_user_id": users["u2"]["id"]})
    assert r.status_code == 200, r.text

def test_only_creator_can_complete(s2, s1, users):
    # Create new tournament
    r = s1.post(f"{API}/tournaments", json={"game_id": pytest.game_id, "stake_amount": 0, "max_players": 4, "start_time": "2026-12-31T10:00:00Z"})
    tid = r.json()["id"]
    r2 = s2.post(f"{API}/tournaments/{tid}/complete", params={"winner_user_id": users["u1"]["id"]})
    assert r2.status_code == 403

def test_leaderboard():
    r = requests.get(f"{API}/leaderboard")
    assert r.status_code == 200 and isinstance(r.json(), list)

def test_wallet_deposit_stripe(s1):
    r = s1.post(f"{API}/wallet/deposit", json={"amount": 10.0, "origin_url": BASE_URL})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "checkout_url" in body and "session_id" in body
    assert "stripe.com" in body["checkout_url"]
    pytest.session_id = body["session_id"]

def test_wallet_status_pending(s1):
    r = s1.get(f"{API}/wallet/deposit/status/{pytest.session_id}")
    assert r.status_code == 200

def test_wallet_deposit_invalid(s1):
    r = s1.post(f"{API}/wallet/deposit", json={"amount": -5, "origin_url": BASE_URL})
    assert r.status_code == 400

def test_unauth_protected():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401
