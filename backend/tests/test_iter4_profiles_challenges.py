"""
Iteration 4 backend tests:
- Profile update (PUT /api/users/profile) + validation
- GET /api/users/me/profile, /api/users/{user_id}
- GET /api/users/search with combined filters
- GET /api/countries, /api/platforms-list
- POST /api/challenges, GET /api/challenges/incoming
- Private tournament invite-only join enforcement
- get_tournaments hides private from non-invitees
- last_active_at auto-update on authenticated requests
"""
import os, time, requests, pytest
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://esports-bet-3.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
_mc = MongoClient(MONGO_URL)
_db = _mc[DB_NAME]


def _credit(uid, amt):
    _db.users.update_one({"_id": ObjectId(uid)}, {"$inc": {"wallet_balance": amt}})


def _new_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register(s, label):
    t = int(time.time() * 1000) + abs(hash(label)) % 100000
    payload = {"email": f"TEST_{label}_{t}@e.com", "password": "Passw0rd!", "username": f"TEST_{label}_{t}"}
    r = s.post(f"{API}/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _login_admin():
    s = _new_session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@esportsbet.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    return s


def _create_game(s, name=None):
    n = name or f"TEST_G_{int(time.time()*1000)}_{abs(hash(name or 'x'))%10000}"
    r = s.post(f"{API}/games", json={"name": n, "platform": "PC"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


# =====================================================================
# Countries and platforms lists
# =====================================================================
class TestStaticLists:
    def test_countries_list(self):
        s = _new_session(); _register(s, "ct")
        r = s.get(f"{API}/countries")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 35
        for item in data:
            assert "code" in item and "name" in item
            assert isinstance(item["code"], str)
        codes = [c["code"] for c in data]
        assert "AU" in codes and "US" in codes and "OTHER" in codes

    def test_platforms_list(self):
        s = _new_session(); _register(s, "pl")
        r = s.get(f"{API}/platforms-list")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 7
        codes = {p["code"] for p in data}
        assert codes == {"ps5", "ps4", "xbox_series", "xbox_one", "pc", "switch", "mobile"}


# =====================================================================
# Profile update + validation
# =====================================================================
class TestProfileUpdate:
    def test_update_full_profile_returns_public_profile(self):
        s = _new_session()
        u = _register(s, "pu")
        admin = _login_admin()
        gid = _create_game(admin)
        payload = {
            "bio": "Pro AU player",
            "country": "AU",
            "city": "Sydney",
            "timezone": "Australia/Sydney",
            "platforms": ["ps5", "pc"],
            "gamertags": {"psn": "myPSN", "steam": "mySteam"},
            "preferred_game_ids": [gid],
            "stake_min": 10.0,
            "stake_max": 100.0,
        }
        r = s.put(f"{API}/users/profile", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == u["id"]
        assert body["bio"] == "Pro AU player"
        assert body["country"] == "AU"
        assert body["city"] == "Sydney"
        assert body["timezone"] == "Australia/Sydney"
        assert set(body["platforms"]) == {"ps5", "pc"}
        assert body["gamertags"]["psn"] == "myPSN"
        assert body["preferred_game_ids"] == [gid]
        assert len(body["preferred_games"]) == 1
        assert body["preferred_games"][0]["id"] == gid
        assert body["preferred_games"][0]["name"]
        assert body["preferred_games"][0]["platform"] == "PC"
        assert body["stake_min"] == 10.0 and body["stake_max"] == 100.0
        # no password, no email leakage
        assert "password_hash" not in body
        assert "email" not in body

    def test_invalid_platform_returns_400(self):
        s = _new_session(); _register(s, "ip")
        r = s.put(f"{API}/users/profile", json={"platforms": ["ps5", "nintendo64"]})
        assert r.status_code == 400, r.text
        assert "Invalid platforms" in r.json()["detail"]

    def test_invalid_game_returns_400(self):
        s = _new_session(); _register(s, "ig")
        bogus = str(ObjectId())
        r = s.put(f"{API}/users/profile", json={"preferred_game_ids": [bogus]})
        assert r.status_code == 400, r.text
        assert "does not exist" in r.json()["detail"]

    def test_stake_min_gt_max_returns_400(self):
        s = _new_session(); _register(s, "sm")
        r = s.put(f"{API}/users/profile", json={"stake_min": 500.0, "stake_max": 10.0})
        assert r.status_code == 400, r.text
        assert "stake_min" in r.json()["detail"]


# =====================================================================
# Profile fetch
# =====================================================================
class TestProfileFetch:
    def test_get_my_profile(self):
        s = _new_session(); u = _register(s, "gmp")
        s.put(f"{API}/users/profile", json={"bio": "hello", "country": "us"})
        r = s.get(f"{API}/users/me/profile")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == u["id"]
        assert body["bio"] == "hello"
        # country stored as provided (server doesn't uppercase on PUT)
        assert body["country"] in ("us", "US")

    def test_get_other_user_profile_no_email_leak(self):
        s1, s2 = _new_session(), _new_session()
        u1 = _register(s1, "go1"); u2 = _register(s2, "go2")
        r = s1.get(f"{API}/users/{u2['id']}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == u2["id"]
        assert body["username"] == u2["username"]
        assert "password_hash" not in body
        assert "email" not in body

    def test_get_user_profile_invalid_id_returns_404(self):
        s = _new_session(); _register(s, "gni")
        r = s.get(f"{API}/users/not-a-valid-objectid")
        assert r.status_code == 404, r.text

    def test_get_user_profile_missing_returns_404(self):
        s = _new_session(); _register(s, "gnm")
        r = s.get(f"{API}/users/{str(ObjectId())}")
        assert r.status_code == 404, r.text


# =====================================================================
# Search filters
# =====================================================================
class TestUserSearch:
    def test_search_excludes_self_and_filters(self):
        s_admin = _login_admin()
        gid_a = _create_game(s_admin, f"TEST_SearchGameA_{int(time.time()*1000)}")
        gid_b = _create_game(s_admin, f"TEST_SearchGameB_{int(time.time()*1000)+1}")

        s_me = _new_session(); me = _register(s_me, "srm")
        s_a = _new_session(); ua = _register(s_a, "sra")
        s_b = _new_session(); ub = _register(s_b, "srb")

        # me prefers game A
        s_me.put(f"{API}/users/profile", json={"country": "AU", "platforms": ["pc"],
                                                 "preferred_game_ids": [gid_a],
                                                 "stake_min": 10.0, "stake_max": 100.0})
        # ua: AU, ps5, prefers gid_a, stake 20-80, total_wins set high via mongo
        s_a.put(f"{API}/users/profile", json={"country": "AU", "platforms": ["ps5", "pc"],
                                               "preferred_game_ids": [gid_a],
                                               "stake_min": 20.0, "stake_max": 80.0,
                                               "bio": "looking for FPS matches"})
        _db.users.update_one({"_id": ObjectId(ua["id"])}, {"$set": {"total_wins": 5}})
        # ub: US, xbox_series, prefers gid_b, stake 500-1000
        s_b.put(f"{API}/users/profile", json={"country": "US", "platforms": ["xbox_series"],
                                               "preferred_game_ids": [gid_b],
                                               "stake_min": 500.0, "stake_max": 1000.0})

        # Filter by country=AU should include ua but not ub or self
        r = s_me.get(f"{API}/users/search", params={"country": "AU"})
        assert r.status_code == 200, r.text
        ids = [x["id"] for x in r.json()]
        assert ua["id"] in ids
        assert ub["id"] not in ids
        assert me["id"] not in ids

        # Filter by lowercase country -> should still match (server uppercases)
        r2 = s_me.get(f"{API}/users/search", params={"country": "au"})
        ids2 = [x["id"] for x in r2.json()]
        assert ua["id"] in ids2

        # Platform filter ps5
        r3 = s_me.get(f"{API}/users/search", params={"platform": "ps5"})
        ids3 = [x["id"] for x in r3.json()]
        assert ua["id"] in ids3
        assert ub["id"] not in ids3

        # game_id filter
        r4 = s_me.get(f"{API}/users/search", params={"game_id": gid_b})
        ids4 = [x["id"] for x in r4.json()]
        assert ub["id"] in ids4
        assert ua["id"] not in ids4

        # min_wins filter
        r5 = s_me.get(f"{API}/users/search", params={"min_wins": 3})
        ids5 = [x["id"] for x in r5.json()]
        assert ua["id"] in ids5
        assert ub["id"] not in ids5

        # stake range overlap: requested 10-50 should match ua (20-80) not ub (500-1000)
        r6 = s_me.get(f"{API}/users/search", params={"stake_min": 10, "stake_max": 50})
        ids6 = [x["id"] for x in r6.json()]
        assert ua["id"] in ids6
        assert ub["id"] not in ids6

        # free-text q on bio
        r7 = s_me.get(f"{API}/users/search", params={"q": "FPS"})
        ids7 = [x["id"] for x in r7.json()]
        assert ua["id"] in ids7

        # is_online flag exists on results
        for entry in r.json():
            assert "is_online" in entry

    def test_search_online_only(self):
        # An online user (just authenticated) and a stale user
        s_me = _new_session(); _register(s_me, "som")
        s_online = _new_session(); u_on = _register(s_online, "son")
        # Trigger an authenticated request to set last_active_at, then wait briefly
        s_online.get(f"{API}/auth/me")
        time.sleep(1.5)

        # Stale user: set last_active_at to 1 hour ago
        s_stale = _new_session(); u_st = _register(s_stale, "sst")
        old_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        _db.users.update_one({"_id": ObjectId(u_st["id"])}, {"$set": {"last_active_at": old_iso}})

        r = s_me.get(f"{API}/users/search", params={"online_only": "true"})
        assert r.status_code == 200, r.text
        ids = [x["id"] for x in r.json()]
        assert u_on["id"] in ids
        assert u_st["id"] not in ids


# =====================================================================
# last_active_at auto-update
# =====================================================================
class TestLastActiveAt:
    def test_last_active_at_updates_on_auth_request(self):
        s = _new_session(); u = _register(s, "la")
        # explicitly null it
        _db.users.update_one({"_id": ObjectId(u["id"])}, {"$set": {"last_active_at": None}})
        # Make an authenticated call
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        # The update is fire-and-forget asyncio.create_task — wait briefly
        time.sleep(1.5)
        doc = _db.users.find_one({"_id": ObjectId(u["id"])})
        assert doc.get("last_active_at") is not None
        # Parse and ensure recent (within 60s)
        ts = datetime.fromisoformat(doc["last_active_at"].replace("Z", "+00:00"))
        delta = abs((datetime.now(timezone.utc) - ts).total_seconds())
        assert delta < 60, f"last_active_at not recent: {doc['last_active_at']}"


# =====================================================================
# Challenges (private 1v1 tournament)
# =====================================================================
class TestChallenges:
    def _setup(self, challenger_label, opponent_label):
        admin = _login_admin()
        gid = _create_game(admin)
        s1 = _new_session(); u1 = _register(s1, challenger_label)
        s2 = _new_session(); u2 = _register(s2, opponent_label)
        _credit(u1["id"], 1000.0); _credit(u2["id"], 1000.0)
        return s1, u1, s2, u2, gid

    def test_create_challenge_success(self):
        s1, u1, s2, u2, gid = self._setup("ch1a", "ch1b")
        pre = s1.get(f"{API}/auth/me").json()["wallet_balance"]
        r = s1.post(f"{API}/challenges", json={
            "opponent_user_id": u2["id"], "game_id": gid,
            "stake_amount": 50.0, "start_time": "2026-12-31T10:00:00Z"
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert "tournament_id" in body
        assert body["opponent_username"] == u2["username"]
        assert body["stake_amount"] == 50.0
        # Stake deducted
        post = s1.get(f"{API}/auth/me").json()["wallet_balance"]
        assert round(pre - post, 2) == 50.0
        # Verify private tournament fields
        tid = body["tournament_id"]
        tdoc = _db.tournaments.find_one({"_id": ObjectId(tid)})
        assert tdoc["is_private"] is True
        assert u2["id"] in tdoc["invited_user_ids"]
        assert tdoc["current_players"] == 1
        assert tdoc["max_players"] == 2

    def test_self_challenge_400(self):
        s1, u1, s2, u2, gid = self._setup("ch2a", "ch2b")
        r = s1.post(f"{API}/challenges", json={
            "opponent_user_id": u1["id"], "game_id": gid,
            "stake_amount": 50.0, "start_time": "2026-12-31T10:00:00Z"
        })
        assert r.status_code == 400, r.text

    def test_zero_or_negative_stake_400(self):
        s1, u1, s2, u2, gid = self._setup("ch3a", "ch3b")
        for amt in (0.0, -10.0):
            r = s1.post(f"{API}/challenges", json={
                "opponent_user_id": u2["id"], "game_id": gid,
                "stake_amount": amt, "start_time": "2026-12-31T10:00:00Z"
            })
            assert r.status_code == 400, (amt, r.text)

    def test_missing_opponent_404(self):
        s1, u1, s2, u2, gid = self._setup("ch4a", "ch4b")
        r = s1.post(f"{API}/challenges", json={
            "opponent_user_id": str(ObjectId()), "game_id": gid,
            "stake_amount": 50.0, "start_time": "2026-12-31T10:00:00Z"
        })
        assert r.status_code == 404, r.text

    def test_missing_game_404(self):
        s1, u1, s2, u2, gid = self._setup("ch5a", "ch5b")
        r = s1.post(f"{API}/challenges", json={
            "opponent_user_id": u2["id"], "game_id": str(ObjectId()),
            "stake_amount": 50.0, "start_time": "2026-12-31T10:00:00Z"
        })
        assert r.status_code == 404, r.text

    def test_insufficient_balance_400(self):
        s1, u1, s2, u2, gid = self._setup("ch6a", "ch6b")
        # drain s1
        bal = s1.get(f"{API}/auth/me").json()["wallet_balance"]
        _db.users.update_one({"_id": ObjectId(u1["id"])}, {"$set": {"wallet_balance": 5.0}})
        r = s1.post(f"{API}/challenges", json={
            "opponent_user_id": u2["id"], "game_id": gid,
            "stake_amount": 50.0, "start_time": "2026-12-31T10:00:00Z"
        })
        assert r.status_code == 400, r.text
        assert "Insufficient" in r.json()["detail"]

    def test_incoming_challenges_list(self):
        s1, u1, s2, u2, gid = self._setup("ic1a", "ic1b")
        cr = s1.post(f"{API}/challenges", json={
            "opponent_user_id": u2["id"], "game_id": gid,
            "stake_amount": 25.0, "start_time": "2026-12-31T10:00:00Z"
        })
        tid = cr.json()["tournament_id"]

        # Opponent should see incoming
        r = s2.get(f"{API}/challenges/incoming")
        assert r.status_code == 200, r.text
        rows = r.json()
        match = next((x for x in rows if x["tournament_id"] == tid), None)
        assert match is not None, rows
        assert match["challenger_username"] == u1["username"]
        assert match["stake_amount"] == 25.0
        assert match["game_platform"] == "PC"
        assert match["game_name"]

        # Challenger should NOT see it in their incoming
        r2 = s1.get(f"{API}/challenges/incoming")
        ids = [x["tournament_id"] for x in r2.json()]
        assert tid not in ids

    def test_private_tournament_join_invite_only(self):
        s1, u1, s2, u2, gid = self._setup("pj1a", "pj1b")
        # Third party
        s3 = _new_session(); u3 = _register(s3, "pj1c")
        _credit(u3["id"], 1000.0)

        cr = s1.post(f"{API}/challenges", json={
            "opponent_user_id": u2["id"], "game_id": gid,
            "stake_amount": 40.0, "start_time": "2026-12-31T10:00:00Z"
        })
        tid = cr.json()["tournament_id"]

        # Non-invitee cannot join
        rj = s3.post(f"{API}/tournaments/{tid}/join")
        assert rj.status_code == 403, rj.text
        assert "invited" in rj.json()["detail"].lower()

        # Invitee can join -> auto-starts
        rj2 = s2.post(f"{API}/tournaments/{tid}/join")
        assert rj2.status_code == 200, rj2.text
        d = s2.get(f"{API}/tournaments/{tid}").json()
        assert d["status"] == "in_progress"
        assert d["current_players"] == 2

        # After joining, opponent no longer sees it in incoming
        r_inc = s2.get(f"{API}/challenges/incoming")
        ids = [x["tournament_id"] for x in r_inc.json()]
        assert tid not in ids

    def test_private_hidden_from_public_listing(self):
        s1, u1, s2, u2, gid = self._setup("ph1a", "ph1b")
        # Third party
        s3 = _new_session(); u3 = _register(s3, "ph1c")

        cr = s1.post(f"{API}/challenges", json={
            "opponent_user_id": u2["id"], "game_id": gid,
            "stake_amount": 30.0, "start_time": "2026-12-31T10:00:00Z"
        })
        tid = cr.json()["tournament_id"]

        # Non-invitee s3 sees nothing for this id
        r_pub = s3.get(f"{API}/tournaments")
        ids_pub = [t["id"] for t in r_pub.json()]
        assert tid not in ids_pub

        # Creator sees it
        r_cr = s1.get(f"{API}/tournaments")
        assert tid in [t["id"] for t in r_cr.json()]
        # Invitee sees it
        r_in = s2.get(f"{API}/tournaments")
        assert tid in [t["id"] for t in r_in.json()]
