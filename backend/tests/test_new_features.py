"""
Tests for iteration 3 new features:
- Tournament state machine (open -> in_progress -> pending_confirmation -> completed|disputed)
- POST /tournaments/{id}/submit-result (both-players-confirm flow + dispute)
- Auto-start when full
- Evidence upload/list/download (object storage)
- Latency record/list (HTTP)
- WebSocket /api/ws/latency ping/report
- Admin dispute resolution via /tournaments/{id}/complete
- Welcome bonus (1000), daily bonus (250), role field on UserResponse
"""
import os, io, time, json, asyncio, requests, pytest
from pymongo import MongoClient
from bson import ObjectId
from PIL import Image
import websockets

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://esports-bet-3.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"
WS_BASE = BASE_URL.replace("https://", "wss://").replace("http://", "ws://")

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
_mc = MongoClient(MONGO_URL)
_db = _mc[DB_NAME]


def _credit(uid, amt):
    _db.users.update_one({"_id": ObjectId(uid)}, {"$inc": {"wallet_balance": amt}})


def _png_bytes(color="red", size=(80, 80)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO(); img.save(buf, "PNG"); return buf.getvalue()


def _multipart_post(session, url, files):
    """Send multipart POST using session cookies/auth but NOT its JSON content-type."""
    return requests.post(url, files=files, cookies=session.cookies)


def _get_with_cookies(session, url):
    return requests.get(url, cookies=session.cookies)


def _new_session():
    s = requests.Session(); s.headers.update({"Content-Type": "application/json"}); return s


def _register(s, label):
    t = int(time.time() * 1000) + hash(label) % 10000
    payload = {"email": f"TEST_{label}_{t}@e.com", "password": "Passw0rd!", "username": f"TEST_{label}_{t}"}
    r = s.post(f"{API}/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _login_admin():
    s = _new_session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@esportsbet.com", "password": "admin123"})
    assert r.status_code == 200, r.text
    return s, r.json()


def _create_game(s):
    r = s.post(f"{API}/games", json={"name": f"TEST_G_{int(time.time()*1000)}", "platform": "PC"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _make_tournament_2p(creator_s, joiner_s, stake=50.0):
    """Create a 2-player tournament, joiner joins -> auto-starts to in_progress."""
    creator = creator_s.get(f"{API}/auth/me").json()
    joiner = joiner_s.get(f"{API}/auth/me").json()
    _credit(creator["id"], 1000.0); _credit(joiner["id"], 1000.0)
    gid = _create_game(creator_s)
    r = creator_s.post(f"{API}/tournaments", json={
        "game_id": gid, "stake_amount": stake, "max_players": 2,
        "start_time": "2026-12-31T10:00:00Z"
    })
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    jr = joiner_s.post(f"{API}/tournaments/{tid}/join")
    assert jr.status_code == 200, jr.text
    return tid, creator, joiner


# =====================================================================
# Welcome bonus + role on UserResponse
# =====================================================================
class TestWelcomeBonusAndRole:
    def test_new_user_gets_welcome_bonus_and_role_null(self):
        s = _new_session()
        u = _register(s, "wb")
        assert u["wallet_balance"] == 1000.0
        assert u["role"] is None
        # Verify transaction logged
        me = s.get(f"{API}/auth/me").json()
        assert me["role"] is None
        # Check welcome_bonus transaction exists
        tx = s.get(f"{API}/wallet/transactions").json()
        assert any(t["reference_type"] == "welcome_bonus" and t["amount"] == 1000.0 for t in tx), tx

    def test_admin_login_has_admin_role(self):
        s, body = _login_admin()
        assert body["role"] == "admin"
        me = s.get(f"{API}/auth/me").json()
        assert me["role"] == "admin"


# =====================================================================
# Daily bonus
# =====================================================================
class TestDailyBonus:
    def test_can_claim_then_blocks(self):
        s = _new_session()
        u = _register(s, "db")
        # Reset last_daily_bonus in case
        _db.users.update_one({"_id": ObjectId(u["id"])}, {"$set": {"last_daily_bonus": None}})

        st = s.get(f"{API}/wallet/daily-bonus/status").json()
        assert st["can_claim"] is True

        c = s.post(f"{API}/wallet/daily-bonus")
        assert c.status_code == 200, c.text
        assert c.json()["amount"] == 250.0

        # second attempt should fail
        c2 = s.post(f"{API}/wallet/daily-bonus")
        assert c2.status_code == 400, c2.text

        st2 = s.get(f"{API}/wallet/daily-bonus/status").json()
        assert st2["can_claim"] is False
        assert st2["hours_remaining"] > 0


# =====================================================================
# Auto-start state machine + submit-result happy path (agreement)
# =====================================================================
class TestStateMachineAndSubmitResult:
    def test_auto_start_on_full(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "sm1"); _register(s2, "sm2")
        tid, c, j = _make_tournament_2p(s1, s2)
        d = s1.get(f"{API}/tournaments/{tid}").json()
        assert d["status"] == "in_progress", d
        assert d.get("started_at") is not None

    def test_submit_result_only_participant(self):
        s1, s2, s3 = _new_session(), _new_session(), _new_session()
        _register(s1, "sr1"); _register(s2, "sr2"); _register(s3, "sr3")
        tid, c, j = _make_tournament_2p(s1, s2)
        r = s3.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": c["id"]})
        assert r.status_code == 403, r.text

    def test_submit_result_winner_must_be_participant(self):
        s1, s2, s3 = _new_session(), _new_session(), _new_session()
        _register(s1, "wp1"); _register(s2, "wp2"); u3 = _register(s3, "wp3")
        tid, c, j = _make_tournament_2p(s1, s2)
        r = s1.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": u3["id"]})
        assert r.status_code == 400, r.text

    def test_pending_confirmation_after_first_submit(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "pc1"); _register(s2, "pc2")
        tid, c, j = _make_tournament_2p(s1, s2)
        r = s1.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": c["id"]})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "pending_confirmation"
        d = s1.get(f"{API}/tournaments/{tid}").json()
        assert d["status"] == "pending_confirmation"

    def test_agreement_auto_payout(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "ag1"); _register(s2, "ag2")
        tid, c, j = _make_tournament_2p(s1, s2, stake=100.0)
        pre = s2.get(f"{API}/auth/me").json()["wallet_balance"]
        s1.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": j["id"]})
        r = s2.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": j["id"]})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "completed"
        assert body["winner_id"] == j["id"]
        # 100*2*0.95 = 190
        assert body["winner_amount"] == 190.0
        post = s2.get(f"{API}/auth/me").json()["wallet_balance"]
        assert round(post - pre, 2) == 190.0
        d = s1.get(f"{API}/tournaments/{tid}").json()
        assert d["status"] == "completed"
        assert d["resolution"] == "auto_agreement"

    def test_disagreement_creates_dispute(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "dp1"); _register(s2, "dp2")
        tid, c, j = _make_tournament_2p(s1, s2)
        s1.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": c["id"]})
        r = s2.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": j["id"]})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "disputed"
        d = s1.get(f"{API}/tournaments/{tid}").json()
        assert d["status"] == "disputed"
        assert d.get("disputed_at") is not None

    def test_admin_resolves_dispute(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "ar1"); _register(s2, "ar2")
        tid, c, j = _make_tournament_2p(s1, s2, stake=20.0)
        s1.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": c["id"]})
        s2.post(f"{API}/tournaments/{tid}/submit-result", params={"claimed_winner_id": j["id"]})

        admin_s, _ = _login_admin()
        pre = s1.get(f"{API}/auth/me").json()["wallet_balance"]
        r = admin_s.post(f"{API}/tournaments/{tid}/complete", params={"winner_user_id": c["id"]})
        assert r.status_code == 200, r.text
        # 20*2*0.95 = 38
        assert r.json()["winner_amount"] == 38.0
        d = s1.get(f"{API}/tournaments/{tid}").json()
        assert d["status"] == "completed"
        assert d["resolution"] == "admin_resolved"
        assert d["winner_id"] == c["id"]
        post = s1.get(f"{API}/auth/me").json()["wallet_balance"]
        assert round(post - pre, 2) == 38.0


# =====================================================================
# Evidence upload
# =====================================================================
class TestEvidence:
    def test_upload_list_download(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "ev1"); _register(s2, "ev2")
        tid, c, j = _make_tournament_2p(s1, s2)
        png = _png_bytes("blue")
        files = {"file": ("proof.png", png, "image/png")}
        r = _multipart_post(s1, f"{API}/tournaments/{tid}/evidence", files)
        assert r.status_code == 200, r.text
        eid = r.json()["id"]
        assert r.json()["storage_path"]

        lst = s1.get(f"{API}/tournaments/{tid}/evidence")
        assert lst.status_code == 200
        items = lst.json()
        assert any(i["id"] == eid for i in items)
        item = next(i for i in items if i["id"] == eid)
        assert "username" in item and item["username"]

        dl = s1.get(f"{API}/evidence/{eid}/download")
        assert dl.status_code == 200
        assert dl.headers.get("content-type", "").startswith("image/")
        assert len(dl.content) == len(png)

    def test_upload_non_participant_forbidden(self):
        s1, s2, s3 = _new_session(), _new_session(), _new_session()
        _register(s1, "ef1"); _register(s2, "ef2"); _register(s3, "ef3")
        tid, c, j = _make_tournament_2p(s1, s2)
        files = {"file": ("p.png", _png_bytes(), "image/png")}
        r = _multipart_post(s3, f"{API}/tournaments/{tid}/evidence", files)
        assert r.status_code == 403, r.text

    def test_upload_invalid_type_rejected(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "et1"); _register(s2, "et2")
        tid, c, j = _make_tournament_2p(s1, s2)
        files = {"file": ("bad.txt", b"not an image", "text/plain")}
        r = _multipart_post(s1, f"{API}/tournaments/{tid}/evidence", files)
        assert r.status_code == 400, r.text


# =====================================================================
# Latency HTTP + stats
# =====================================================================
class TestLatencyHTTP:
    def test_record_and_get_stats(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "lt1"); _register(s2, "lt2")
        tid, c, j = _make_tournament_2p(s1, s2)
        for ms in (50, 75, 100):
            r = s1.post(f"{API}/tournaments/{tid}/latency", params={"latency_ms": ms})
            assert r.status_code == 200, r.text
        for ms in (200, 300):
            r = s2.post(f"{API}/tournaments/{tid}/latency", params={"latency_ms": ms})
            assert r.status_code == 200, r.text

        stats = s1.get(f"{API}/tournaments/{tid}/latency").json()
        assert isinstance(stats, list) and len(stats) == 2
        by_id = {x["user_id"]: x for x in stats}
        a = by_id[c["id"]]
        assert a["sample_count"] == 3
        assert a["min_ms"] == 50 and a["max_ms"] == 100
        assert a["avg_ms"] == 75.0
        assert len(a["samples"]) == 3

        b = by_id[j["id"]]
        assert b["sample_count"] == 2
        assert b["avg_ms"] == 250.0

    def test_record_latency_non_participant(self):
        s1, s2, s3 = _new_session(), _new_session(), _new_session()
        _register(s1, "ln1"); _register(s2, "ln2"); _register(s3, "ln3")
        tid, c, j = _make_tournament_2p(s1, s2)
        r = s3.post(f"{API}/tournaments/{tid}/latency", params={"latency_ms": 100})
        assert r.status_code == 403, r.text


# =====================================================================
# Latency WebSocket
# =====================================================================
class TestLatencyWebSocket:
    @pytest.mark.asyncio
    async def test_ws_ping_pong_and_report(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "ws1"); _register(s2, "ws2")
        tid, c, j = _make_tournament_2p(s1, s2)
        token = s1.cookies.get("access_token")
        assert token

        url = f"{WS_BASE}/api/ws/latency?tournament_id={tid}&token={token}"
        async with websockets.connect(url, open_timeout=15, ping_interval=None) as ws:
            await ws.send(json.dumps({"type": "ping", "client_ts": 12345}))
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            assert msg["type"] == "pong"
            assert msg["client_ts"] == 12345
            assert isinstance(msg["server_ts"], int)

            await ws.send(json.dumps({"type": "report", "latency_ms": 42.5}))
            await asyncio.sleep(1.5)  # give DB time to record

        stats = s1.get(f"{API}/tournaments/{tid}/latency").json()
        mine = next((x for x in stats if x["user_id"] == c["id"]), None)
        assert mine is not None
        assert any(abs(s["latency_ms"] - 42.5) < 0.01 for s in mine["samples"]), mine

    @pytest.mark.asyncio
    async def test_ws_rejects_non_participant(self):
        s1, s2, s3 = _new_session(), _new_session(), _new_session()
        _register(s1, "wn1"); _register(s2, "wn2"); _register(s3, "wn3")
        tid, c, j = _make_tournament_2p(s1, s2)
        token = s3.cookies.get("access_token")
        url = f"{WS_BASE}/api/ws/latency?tournament_id={tid}&token={token}"
        with pytest.raises(Exception):
            async with websockets.connect(url, open_timeout=15, ping_interval=None) as ws:
                # Server should close with code 4403
                await asyncio.wait_for(ws.recv(), timeout=5)

    @pytest.mark.asyncio
    async def test_ws_rejects_bad_token(self):
        s1, s2 = _new_session(), _new_session()
        _register(s1, "wb1"); _register(s2, "wb2")
        tid, c, j = _make_tournament_2p(s1, s2)
        url = f"{WS_BASE}/api/ws/latency?tournament_id={tid}&token=garbage"
        with pytest.raises(Exception):
            async with websockets.connect(url, open_timeout=15, ping_interval=None) as ws:
                await asyncio.wait_for(ws.recv(), timeout=5)
