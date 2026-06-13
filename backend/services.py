"""Cross-domain helpers shared across routers.

Kept in one module to avoid circular imports between routers. Each function only
imports from `core` (db, app, constants, logger) — never from routers.
"""
from __future__ import annotations

import os
import uuid
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException, Response

from core import (
    db, logger, hash_password,
    APP_NAME, STORAGE_URL, STORAGE_BACKEND, STORAGE_LOCAL_PATH,
    LATENCY_WARN_MS, LATENCY_HIGH_MS,
    DISPUTE_HOLD_THRESHOLD, DISPUTE_HOLD_MIN_MATCHES,
    TWOFA_CODE_TTL_SECONDS,
    create_access_token, create_refresh_token,
)


# ============ STORAGE (local disk by default, Emergent ObjStore optional) ============
_storage_key: Optional[str] = None


def _ensure_local_dir(full_path: str):
    Path(full_path).parent.mkdir(parents=True, exist_ok=True)


def init_storage():
    global _storage_key
    if STORAGE_BACKEND == "local":
        Path(STORAGE_LOCAL_PATH).mkdir(parents=True, exist_ok=True)
        return "local"
    if _storage_key:
        return _storage_key
    emergent_key = os.environ.get("EMERGENT_LLM_KEY")
    if not emergent_key:
        raise RuntimeError("EMERGENT_LLM_KEY not set (required when STORAGE_BACKEND=emergent)")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": emergent_key}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    global _storage_key
    init_storage()
    if STORAGE_BACKEND == "local":
        full = os.path.join(STORAGE_LOCAL_PATH, path)
        _ensure_local_dir(full)
        with open(full, "wb") as fh:
            fh.write(data)
        with open(full + ".meta", "w") as fh:
            fh.write(content_type or "application/octet-stream")
        return {"path": path, "size": len(data), "storage": "local"}
    key = _storage_key
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    if resp.status_code == 403:
        _storage_key = None
        key = init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    global _storage_key
    init_storage()
    if STORAGE_BACKEND == "local":
        full = os.path.join(STORAGE_LOCAL_PATH, path)
        if not os.path.exists(full):
            raise HTTPException(status_code=404, detail="File not found")
        with open(full, "rb") as fh:
            data = fh.read()
        ct = "application/octet-stream"
        if os.path.exists(full + ".meta"):
            with open(full + ".meta", "r") as fh:
                ct = fh.read().strip() or ct
        return data, ct
    key = _storage_key
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 403:
        _storage_key = None
        key = init_storage()
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ============ PROFILE ============
async def build_public_profile(user_doc) -> dict:
    """Convert user doc to public profile dict, populating preferred_games."""
    preferred_ids = user_doc.get("preferred_game_ids") or []
    preferred_games = []
    for gid in preferred_ids:
        try:
            g = await db.games.find_one({"_id": ObjectId(gid)})
            if g:
                preferred_games.append({"id": str(g["_id"]), "name": g["name"], "platform": g["platform"]})
        except Exception:
            continue
    return {
        "id": str(user_doc["_id"]),
        "username": user_doc["username"],
        "bio": user_doc.get("bio"),
        "country": user_doc.get("country"),
        "city": user_doc.get("city"),
        "timezone": user_doc.get("timezone"),
        "platforms": user_doc.get("platforms") or [],
        "gamertags": user_doc.get("gamertags") or {},
        "preferred_game_ids": preferred_ids,
        "preferred_games": preferred_games,
        "stake_min": user_doc.get("stake_min"),
        "stake_max": user_doc.get("stake_max"),
        "total_wins": user_doc.get("total_wins", 0),
        "total_losses": user_doc.get("total_losses", 0),
        "wallet_balance": user_doc.get("wallet_balance", 0.0),
        "last_active_at": user_doc.get("last_active_at"),
        "created_at": user_doc["created_at"],
    }


# ============ ADMIN GATE ============
async def require_admin(user: dict):
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not user_doc or user_doc.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_doc


# ============ TOURNAMENTS CORE ============
async def cleanup_expired_tournaments():
    """Delete tournaments whose start_time has passed but never filled (still 'open'). Refund all participants."""
    now_iso = datetime.now(timezone.utc).isoformat()
    expired = await db.tournaments.find({
        "status": "open",
        "start_time": {"$lt": now_iso}
    }).to_list(1000)
    for t in expired:
        tid = str(t["_id"])
        participants = await db.tournament_participants.find({"tournament_id": tid}).to_list(1000)
        for p in participants:
            await db.users.update_one(
                {"_id": ObjectId(p["user_id"])},
                {"$inc": {"wallet_balance": t["stake_amount"]}}
            )
            await db.wallet_transactions.insert_one({
                "user_id": p["user_id"],
                "amount": t["stake_amount"],
                "type": "credit",
                "reference_type": "tournament_expired_refund",
                "reference_id": tid,
                "timestamp": now_iso,
            })
        await db.tournament_participants.delete_many({"tournament_id": tid})
        await db.tournaments.delete_one({"_id": t["_id"]})


async def award_winner_and_close(tournament_id: str, winner_user_id: str, resolution: str):
    """Helper: pays out winner, updates losers, marks tournament completed."""
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    total_pool = tournament["stake_amount"] * tournament["current_players"]
    platform_fee = total_pool * 0.05
    winner_amount = total_pool - platform_fee

    await db.users.update_one({"_id": ObjectId(winner_user_id)}, {"$inc": {"wallet_balance": winner_amount, "total_wins": 1}})
    await db.wallet_transactions.insert_one({
        "user_id": winner_user_id,
        "amount": winner_amount,
        "type": "credit",
        "reference_type": "tournament_win",
        "reference_id": tournament_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(1000)
    for p in participants:
        if p["user_id"] != winner_user_id:
            await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"total_losses": 1}})

    await db.tournaments.update_one(
        {"_id": ObjectId(tournament_id)},
        {"$set": {"status": "completed", "winner_id": winner_user_id, "resolution": resolution, "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    return winner_amount


# ============ LATENCY ============
async def compute_latency_advantage_from_samples(samples: list):
    """Generic engine: takes raw {user_id, latency_ms} samples and returns the
    tie-breaker payload. Reused by both tournaments and head-to-head competitions."""
    if not samples:
        return {"advantage_user_id": None, "policy": "lower_avg_ms_wins_ties", "breakdown": []}
    by_user: Dict[str, list] = {}
    for s in samples:
        by_user.setdefault(s["user_id"], []).append(float(s["latency_ms"]))
    breakdown = []
    for uid, vals in by_user.items():
        avg = sum(vals) / len(vals)
        peak = max(vals)
        if peak >= LATENCY_HIGH_MS:
            status = "high"
        elif avg >= LATENCY_WARN_MS:
            status = "warn"
        else:
            status = "ok"
        u = await db.users.find_one({"_id": ObjectId(uid)})
        breakdown.append({
            "user_id": uid,
            "username": u.get("username") if u else "Unknown",
            "avg_ms": round(avg, 1),
            "max_ms": round(peak, 1),
            "sample_count": len(vals),
            "status": status,
        })
    eligible = [b for b in breakdown if b["sample_count"] >= 3]
    advantage_user_id = None
    if len(eligible) >= 2:
        high_players = [b for b in eligible if b["status"] == "high"]
        low_players = [b for b in eligible if b["status"] != "high"]
        if high_players and low_players and len(high_players) < len(eligible):
            advantage_user_id = min(low_players, key=lambda b: b["avg_ms"])["user_id"]
        else:
            advantage_user_id = min(eligible, key=lambda b: b["avg_ms"])["user_id"]
    return {"advantage_user_id": advantage_user_id, "policy": "lower_avg_ms_wins_ties", "breakdown": breakdown}


async def compute_latency_advantage(tournament_id: str):
    """Tournament-scoped tie-breaker."""
    samples = await db.tournament_latency.find({"tournament_id": tournament_id}).to_list(10000)
    return await compute_latency_advantage_from_samples(samples)


async def compute_competition_latency_advantage(competition_id: str, match_id: Optional[str] = None):
    """Head-to-head competition tie-breaker. If match_id is provided, only samples
    tagged to that specific match count. Otherwise all samples across the rivalry
    are used (good fallback when players didn't tag a match)."""
    query: Dict[str, Any] = {"competition_id": competition_id}
    if match_id:
        match_samples = await db.competition_latency.find({"competition_id": competition_id, "match_id": match_id}).to_list(10000)
        if match_samples:
            return await compute_latency_advantage_from_samples(match_samples)
    samples = await db.competition_latency.find(query).to_list(10000)
    return await compute_latency_advantage_from_samples(samples)


# ============ DISPUTE STATUS (auto account hold) ============
async def recompute_user_dispute_status(user_id: str):
    """Recompute whether a user's account should be on hold based on their dispute rate.
    Called whenever a tournament/competition match resolves or is disputed."""
    decided = 0
    disputed = 0

    parts = await db.tournament_participants.find({"user_id": user_id}).to_list(5000)
    for p in parts:
        try:
            t = await db.tournaments.find_one({"_id": ObjectId(p["tournament_id"])})
        except Exception:
            continue
        if not t:
            continue
        if t.get("status") == "disputed":
            disputed += 1
            decided += 1
        elif t.get("status") == "completed":
            decided += 1

    comps = await db.competitions.find({"$or": [{"player_a_id": user_id}, {"player_b_id": user_id}]}).to_list(2000)
    for c in comps:
        ms = await db.competition_matches.find({"competition_id": c["id"]}).to_list(5000)
        for m in ms:
            if m.get("status") == "confirmed":
                decided += 1
            elif m.get("status") == "cancelled":
                decided += 1
                disputed += 1

    rate = (disputed / decided) if decided > 0 else 0.0
    should_hold = decided >= DISPUTE_HOLD_MIN_MATCHES and rate >= DISPUTE_HOLD_THRESHOLD
    update = {
        "$set": {
            "dispute_stats": {
                "decided": decided,
                "disputed": disputed,
                "rate": round(rate, 3),
            }
        }
    }
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    cur_status = (user_doc or {}).get("status")
    if should_hold and cur_status != "on_hold":
        update["$set"]["status"] = "on_hold"
        update["$set"]["on_hold_reason"] = (
            f"Auto-suspended: {disputed}/{decided} matches resolved as disputes ({int(rate*100)}%). "
            "Account is paused pending admin review."
        )
        update["$set"]["on_hold_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"_id": ObjectId(user_id)}, update)
    return {"decided": decided, "disputed": disputed, "rate": rate, "on_hold": should_hold}


# ============ COMPETITIONS ============
async def competition_to_dict(comp: dict) -> dict:
    game = await db.games.find_one({"_id": ObjectId(comp["game_id"])})
    a = await db.users.find_one({"_id": ObjectId(comp["player_a_id"])})
    b = await db.users.find_one({"_id": ObjectId(comp["player_b_id"])})
    return {
        "id": comp["id"],
        "player_a_id": comp["player_a_id"],
        "player_a_username": a["username"] if a else "Unknown",
        "player_b_id": comp["player_b_id"],
        "player_b_username": b["username"] if b else "Unknown",
        "game_id": comp["game_id"],
        "game_name": game["name"] if game else "Unknown",
        "platform": comp.get("platform", ""),
        "stake_per_match": comp["stake_per_match"],
        "wins_a": comp.get("wins_a", 0),
        "wins_b": comp.get("wins_b", 0),
        "total_matches": comp.get("total_matches", 0),
        "status": comp.get("status", "active"),
        "created_at": comp["created_at"],
    }


# ============ PRIZE FEAT TRACKING ============
async def stats_for_user(user_id: str) -> dict:
    """Compute running stats for feat checks. Aggregates wins/streaks from tournaments + h2h competitions."""
    stats = {
        "tournament_wins": 0,
        "h2h_wins": 0,
        "current_streak": 0,
        "wins_by_genre": {},
        "streak_by_genre": {},
        "net_credits": 0.0,
    }
    timeline = []

    parts = await db.tournament_participants.find({"user_id": user_id}).to_list(5000)
    for p in parts:
        try:
            t = await db.tournaments.find_one({"_id": ObjectId(p["tournament_id"])})
        except Exception:
            continue
        if not t or t.get("status") != "completed" or not t.get("winner_id"):
            continue
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])}) if t.get("game_id") else None
        genre = (game or {}).get("category") or "Other"
        won = t["winner_id"] == user_id
        ts = t.get("completed_at") or t.get("created_at") or ""
        timeline.append({"ts": ts, "won": won, "genre": genre, "stake": float(t.get("stake_amount", 0)), "n_players": int(t.get("max_players", 2))})
        if won:
            stats["tournament_wins"] += 1
            stats["wins_by_genre"][genre] = stats["wins_by_genre"].get(genre, 0) + 1
            stats["net_credits"] += float(t.get("stake_amount", 0)) * (int(t.get("max_players", 2)) - 1)
        else:
            stats["net_credits"] -= float(t.get("stake_amount", 0))

    comps = await db.competitions.find({"$or": [{"player_a_id": user_id}, {"player_b_id": user_id}]}).to_list(2000)
    for c in comps:
        game = await db.games.find_one({"_id": ObjectId(c["game_id"])}) if c.get("game_id") else None
        genre = (game or {}).get("category") or "Other"
        matches = await db.competition_matches.find({"competition_id": c["id"], "status": "confirmed"}).to_list(5000)
        for m in matches:
            won = m.get("winner_user_id") == user_id
            ts = m.get("resolved_at") or m.get("created_at") or ""
            timeline.append({"ts": ts, "won": won, "genre": genre, "stake": float(m.get("stake_amount", 0))})
            if won:
                stats["h2h_wins"] += 1
                stats["wins_by_genre"][genre] = stats["wins_by_genre"].get(genre, 0) + 1
                stats["net_credits"] += float(m.get("stake_amount", 0))
            else:
                stats["net_credits"] -= float(m.get("stake_amount", 0))

    timeline.sort(key=lambda x: x["ts"])
    current_streak = 0
    streak_by_genre: Dict[str, int] = {}
    longest_streak_by_genre: Dict[str, int] = {}
    for e in timeline:
        if e["won"]:
            current_streak += 1
            streak_by_genre[e["genre"]] = streak_by_genre.get(e["genre"], 0) + 1
            longest_streak_by_genre[e["genre"]] = max(longest_streak_by_genre.get(e["genre"], 0), streak_by_genre[e["genre"]])
        else:
            current_streak = 0
            streak_by_genre[e["genre"]] = 0
    stats["current_streak"] = current_streak
    stats["streak_by_genre"] = longest_streak_by_genre
    return stats


async def check_feat_unlocked(user_id: str, feat: dict) -> dict:
    """Returns {met: bool, progress: int|float, target: int|float} for a prize feat."""
    if not feat or not feat.get("type"):
        return {"met": True, "progress": 0, "target": 0}
    stats = await stats_for_user(user_id)
    ftype = feat.get("type")
    target = float(feat.get("count") or 0)
    genre = (feat.get("genre") or "").strip()
    progress = 0.0
    if ftype == "tournament_wins":
        progress = stats["tournament_wins"]
    elif ftype == "h2h_wins":
        progress = stats["h2h_wins"]
    elif ftype == "wins_in_genre":
        progress = stats["wins_by_genre"].get(genre, 0)
    elif ftype == "streak":
        progress = stats["current_streak"]
    elif ftype == "streak_in_genre":
        progress = stats["streak_by_genre"].get(genre, 0)
    elif ftype == "net_credits":
        progress = stats["net_credits"]
    return {"met": progress >= target, "progress": progress, "target": target}


async def prize_dict(p: dict, with_unlock_for: Optional[str] = None) -> dict:
    base = {
        "id": p["id"],
        "name": p["name"],
        "description": p.get("description", ""),
        "kind": p.get("kind", "image"),
        "cost": p["cost"],
        "asset": p.get("asset", ""),
        "image_url": p.get("image_url") or "",
        "thumb_url": p.get("thumb_url") or p.get("image_url") or "",
        "rarity": p.get("rarity", "common"),
        "feat": p.get("feat") or {},
        "active": p.get("active", True),
        "created_at": p.get("created_at"),
    }
    if with_unlock_for:
        unlock = await check_feat_unlocked(with_unlock_for, base["feat"])
        base["unlocked"] = unlock["met"]
        base["progress"] = unlock["progress"]
        base["target"] = unlock["target"]
    return base


# ---------- Default prize catalog (image placeholders — admin re-uploads images later) ----------
SEED_PRIZES = [
    # ─── Tournament-wins feats ───────────────────────────────────────────────
    {"name": "FIRST WIN",      "cost": 100,  "feat": {"type": "tournament_wins", "count": 1}},
    {"name": "FIVE STACK",     "cost": 500,  "feat": {"type": "tournament_wins", "count": 5}},
    {"name": "TEN HUNTER",     "cost": 1200, "feat": {"type": "tournament_wins", "count": 10}},
    {"name": "TOURNEY KING",   "cost": 3000, "feat": {"type": "tournament_wins", "count": 25}},
    # ─── H2H wins ────────────────────────────────────────────────────────────
    {"name": "RIVAL SLAYER",   "cost": 600,  "feat": {"type": "h2h_wins", "count": 10}},
    {"name": "MOFO MENACE",    "cost": 1500, "feat": {"type": "h2h_wins", "count": 25}},
    # ─── Genre streaks (user-requested 3) ────────────────────────────────────
    {"name": "ASPHALT ASSASSIN","cost": 2000, "feat": {"type": "streak_in_genre", "count": 10, "genre": "Racing"}},
    {"name": "TRIGGER FINGER",  "cost": 2000, "feat": {"type": "streak_in_genre", "count": 10, "genre": "FPS"}},
    {"name": "STRATEGIST",      "cost": 2000, "feat": {"type": "streak_in_genre", "count": 10, "genre": "Strategy"}},
    # ─── Streak agnostic + net credits ───────────────────────────────────────
    {"name": "ON FIRE",         "cost": 1500, "feat": {"type": "streak", "count": 5}},
    {"name": "BIG SPENDER",     "cost": 1000, "feat": {"type": "net_credits", "count": 5000}},
    {"name": "GOAT",            "cost": 5000, "feat": {"type": "net_credits", "count": 25000}},
]


# ============ WHATSAPP / TWILIO ============
def twilio_client():
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    if not sid or not token:
        return None
    try:
        from twilio.rest import Client
        return Client(sid, token)
    except ImportError:
        return None


async def send_whatsapp(to_phone: str, body: str) -> bool:
    """Fire-and-forget WhatsApp message via Twilio. Returns True on success."""
    cli = twilio_client()
    if not cli or not to_phone:
        return False
    sender = os.environ.get("TWILIO_WHATSAPP_FROM", "").strip()
    if not sender:
        return False
    try:
        cli.messages.create(
            from_=f"whatsapp:{sender}" if not sender.startswith("whatsapp:") else sender,
            to=f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
            body=body,
        )
        return True
    except Exception as e:
        logger.warning(f"WhatsApp send failed: {e}")
        return False


# ============ ADMIN 2FA via WhatsApp ============
async def start_admin_2fa(user_doc: dict, response: Response) -> dict:
    """Generate a 6-digit code, WhatsApp it, return challenge id + ttl."""
    from datetime import timedelta as _td
    phone = (user_doc.get("whatsapp_phone") or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail=(
            "Admin 2FA is enabled but no WhatsApp number is on this account. "
            "Sign in once with admin@... then add a WhatsApp number under Profile → Match Reminders."
        ))
    import secrets
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge_id = str(uuid.uuid4())
    await db.twofa_challenges.insert_one({
        "id": challenge_id,
        "user_id": str(user_doc["_id"]),
        "code_hash": hash_password(code),
        "attempts": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + _td(seconds=TWOFA_CODE_TTL_SECONDS)).isoformat(),
    })
    sent = await send_whatsapp(phone,
        f"🔐 GOMOFOS admin sign-in code: {code}\n\nValid for 5 minutes. Don't share this code with anyone.")
    if not sent:
        raise HTTPException(status_code=500, detail=(
            "Couldn't deliver the 2FA code via WhatsApp. Check Twilio credentials and "
            "make sure your admin WhatsApp number has joined the Twilio sandbox."
        ))
    return {"requires_2fa": True, "challenge_id": challenge_id, "expires_in": TWOFA_CODE_TTL_SECONDS}


# ============ TOURNAMENT REMINDER SCHEDULER ============
async def dispatch_tournament_reminder(t: dict, window: str):
    """Send a single reminder message to every participant in tournament t."""
    game = await db.games.find_one({"_id": ObjectId(t["game_id"])}) if t.get("game_id") else None
    game_name = (game or {}).get("name", "Match")
    parts = await db.tournament_participants.find({"tournament_id": str(t["_id"])}).to_list(100)
    when_label = "in 24 hours" if window == "24h" else "in about 1 hour"
    app_url = os.environ.get("FRONTEND_URL", "https://gomofos.com")
    for p in parts:
        u = await db.users.find_one({"_id": ObjectId(p["user_id"])})
        if not u:
            continue
        phone = (u.get("whatsapp_phone") or u.get("phone") or "").strip()
        if not phone:
            continue
        body = (
            f"🎮 GOMOFOS reminder: your {game_name} tournament starts {when_label}.\n\n"
            f"Stake: {t.get('stake_amount', 0)} CR\n"
            f"Players: {t.get('current_players', 1)}/{t.get('max_players', 2)}\n\n"
            f"Open: {app_url.rstrip('/')}/tournament/{t['_id']}"
        )
        await send_whatsapp(phone, body)


async def reminder_scheduler_loop():
    """Background task: every 60s, find tournaments starting in 24h or 1h and notify participants
    via WhatsApp. Each (tournament, reminder_window) is sent only once."""
    import asyncio
    from datetime import timedelta as _td
    while True:
        try:
            now = datetime.now(timezone.utc)
            cutoff = (now + _td(hours=25)).isoformat()
            cursor = db.tournaments.find({
                "status": {"$in": ["open", "in_progress"]},
                "start_time": {"$lte": cutoff, "$gte": now.isoformat()},
            })
            tournaments = await cursor.to_list(500)
            for t in tournaments:
                try:
                    start = datetime.fromisoformat(t["start_time"])
                    if start.tzinfo is None:
                        start = start.replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                mins_until = (start - now).total_seconds() / 60.0
                sent = t.get("reminders_sent") or []
                # 24h window: 23.0–24.5 h before start
                if 23 * 60 <= mins_until <= 24.5 * 60 and "24h" not in sent:
                    await dispatch_tournament_reminder(t, "24h")
                    await db.tournaments.update_one({"_id": t["_id"]}, {"$addToSet": {"reminders_sent": "24h"}})
                # 1h window: 50–75 min before start
                if 50 <= mins_until <= 75 and "1h" not in sent:
                    await dispatch_tournament_reminder(t, "1h")
                    await db.tournaments.update_one({"_id": t["_id"]}, {"$addToSet": {"reminders_sent": "1h"}})
        except Exception as e:
            logger.warning(f"reminder loop error: {e}")
        await asyncio.sleep(60)


def absolute_base_url() -> str:
    return os.environ.get("PUBLIC_APP_URL") or os.environ.get("FRONTEND_URL", "https://gomofos.com")
