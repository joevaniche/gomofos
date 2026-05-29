import os, time, requests, pytest
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://esports-bet-3.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

# Mongo direct access for seeding wallet balances (test-only utility)
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
_mc = MongoClient(MONGO_URL)
_db = _mc[DB_NAME]

def _credit(user_id: str, amount: float):
    _db.users.update_one({"_id": ObjectId(user_id)}, {"$inc": {"wallet_balance": amount}})

# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def s1():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"}); return s

@pytest.fixture(scope="module")
def s2():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"}); return s

@pytest.fixture(scope="module")
def s3():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"}); return s

@pytest.fixture(scope="module")
def users(s1, s2, s3):
    t = int(time.time())
    u1 = {"email": f"TEST_u1_{t}@e.com", "password": "Passw0rd!", "username": f"TEST_u1_{t}"}
    u2 = {"email": f"TEST_u2_{t}@e.com", "password": "Passw0rd!", "username": f"TEST_u2_{t}"}
    u3 = {"email": f"TEST_u3_{t}@e.com", "password": "Passw0rd!", "username": f"TEST_u3_{t}"}
    r1 = s1.post(f"{API}/auth/register", json=u1); assert r1.status_code == 200, r1.text
    r2 = s2.post(f"{API}/auth/register", json=u2); assert r2.status_code == 200, r2.text
    r3 = s3.post(f"{API}/auth/register", json=u3); assert r3.status_code == 200, r3.text
    j1, j2, j3 = r1.json(), r2.json(), r3.json()
    # Seed wallet balances for staking tests
    _credit(j1["id"], 1000.0)
    _credit(j2["id"], 1000.0)
    _credit(j3["id"], 1000.0)
    return {"u1": j1, "u2": j2, "u3": j3}

# ---------- Auth tests (verify get_current_user fix) ----------
def test_register_and_me(s1, users):
    r = s1.get(f"{API}/auth/me"); assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == users["u1"]["email"]
    assert body["id"] == users["u1"]["id"]
    assert isinstance(body["wallet_balance"], (int, float))

def test_unauth_protected():
    r = requests.get(f"{API}/auth/me")
    assert r.status_code == 401

def test_login_invalid():
    r = requests.post(f"{API}/auth/login", json={"email": "nouser_xyz@x.com", "password": "x"})
    assert r.status_code == 401

def test_login_admin():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@esportsbet.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.cookies

# ---------- Games ----------
def test_create_game_and_list(s1):
    r = s1.post(f"{API}/games", json={"name": "TEST_FIFA24", "platform": "PS5"})
    assert r.status_code == 200, r.text
    gid = r.json()["id"]
    r2 = s1.get(f"{API}/games"); assert r2.status_code == 200
    assert any(g["id"] == gid for g in r2.json())
    pytest.game_id = gid

# ---------- Tournament: validation tests ----------
def test_tournament_stake_zero_rejected(s1):
    r = s1.post(f"{API}/tournaments", json={"game_id": pytest.game_id, "stake_amount": 0, "max_players": 4, "start_time": "2026-12-31T10:00:00Z"})
    assert r.status_code == 400, r.text
    assert "greater than 0" in r.text.lower() or "stake" in r.text.lower()

def test_tournament_stake_negative_rejected(s1):
    r = s1.post(f"{API}/tournaments", json={"game_id": pytest.game_id, "stake_amount": -5, "max_players": 4, "start_time": "2026-12-31T10:00:00Z"})
    assert r.status_code == 400

def test_create_tournament_success(s1):
    r = s1.post(f"{API}/tournaments", json={"game_id": pytest.game_id, "stake_amount": 50, "max_players": 4, "start_time": "2026-12-31T10:00:00Z"})
    assert r.status_code == 200, r.text
    pytest.tournament_id = r.json()["id"]
    assert r.json()["current_players"] == 1
    assert r.json()["stake_amount"] == 50

def test_list_tournaments(s1):
    r = s1.get(f"{API}/tournaments"); assert r.status_code == 200
    assert any(t["id"] == pytest.tournament_id for t in r.json())

def test_list_tournaments_filtered(s1):
    r = s1.get(f"{API}/tournaments?status=open")
    assert r.status_code == 200
    assert all(t["status"] == "open" for t in r.json())

def test_join_tournament(s2):
    r = s2.post(f"{API}/tournaments/{pytest.tournament_id}/join")
    assert r.status_code == 200, r.text

def test_join_tournament_duplicate(s2):
    r = s2.post(f"{API}/tournaments/{pytest.tournament_id}/join")
    assert r.status_code == 400

def test_tournament_details(s1):
    r = s1.get(f"{API}/tournaments/{pytest.tournament_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["current_players"] == 2
    assert len(body["participants"]) == 2

# ---------- Chat: participant restriction tests ----------
def test_chat_non_participant_forbidden(s3, users):
    # u3 has not joined the tournament
    r = s3.post(f"{API}/chat", json={"tournament_id": pytest.tournament_id, "message": "intruder"})
    assert r.status_code == 403, r.text

def test_chat_participants_can_post(s1, s2):
    r = s1.post(f"{API}/chat", json={"tournament_id": pytest.tournament_id, "message": "hi from u1"})
    assert r.status_code == 200, r.text
    r2 = s2.post(f"{API}/chat", json={"tournament_id": pytest.tournament_id, "message": "yo from u2"})
    assert r2.status_code == 200, r2.text
    g = s1.get(f"{API}/chat/{pytest.tournament_id}")
    assert g.status_code == 200 and len(g.json()) >= 2
    messages = [m["message"] for m in g.json()]
    assert "hi from u1" in messages and "yo from u2" in messages

# ---------- Tournament completion: winner-must-be-participant ----------
def test_complete_winner_must_be_participant(s1, users):
    # u3 is not a participant
    r = s1.post(f"{API}/tournaments/{pytest.tournament_id}/complete", params={"winner_user_id": users["u3"]["id"]})
    assert r.status_code == 400, r.text
    assert "participant" in r.text.lower()

def test_only_creator_can_complete(s1, s2, users):
    r2 = s2.post(f"{API}/tournaments/{pytest.tournament_id}/complete", params={"winner_user_id": users["u2"]["id"]})
    assert r2.status_code == 403

def test_complete_tournament_success(s1, s2, users):
    # u1's wallet before; u2 should win prize pool (50*2*0.95 = 95)
    pre = s2.get(f"{API}/auth/me").json()
    r = s1.post(f"{API}/tournaments/{pytest.tournament_id}/complete", params={"winner_user_id": users["u2"]["id"]})
    assert r.status_code == 200, r.text
    assert r.json()["winner_amount"] == pytest.approx(95.0) if hasattr(pytest, 'approx') else r.json()["winner_amount"] == 95.0
    post = s2.get(f"{API}/auth/me").json()
    assert round(post["wallet_balance"] - pre["wallet_balance"], 2) == 95.0
    assert post["total_wins"] == pre["total_wins"] + 1

def test_complete_already_completed(s1, users):
    r = s1.post(f"{API}/tournaments/{pytest.tournament_id}/complete", params={"winner_user_id": users["u2"]["id"]})
    assert r.status_code == 400

# ---------- Leaderboard ----------
def test_leaderboard():
    r = requests.get(f"{API}/leaderboard")
    assert r.status_code == 200 and isinstance(r.json(), list)

# ---------- Wallet/Stripe ----------
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

def test_wallet_transactions_endpoint(s1):
    r = s1.get(f"{API}/wallet/transactions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
