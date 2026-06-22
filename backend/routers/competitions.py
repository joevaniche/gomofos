"""Head-to-Head competitions: CRUD, log-match, confirm, dispute, latency."""
import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import Depends, HTTPException

from core import api_router, db, logger, get_current_user, DISPUTE_HOLD_THRESHOLD
from email_service import send_dispute_admin_alert
from models import CompetitionCreate, CompetitionMatchLog
from services import (
    competition_to_dict,
    compute_competition_latency_advantage,
    recompute_user_dispute_status,
)


@api_router.post("/competitions")
async def create_competition(data: CompetitionCreate, user: dict = Depends(get_current_user)):
    if data.opponent_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You can't compete against yourself")
    if data.stake_per_match <= 0:
        raise HTTPException(status_code=400, detail="Stake must be greater than 0")
    if not data.platform or not data.platform.strip():
        raise HTTPException(status_code=400, detail="Platform required")

    opponent = await db.users.find_one({"_id": ObjectId(data.opponent_user_id)})
    if not opponent:
        raise HTTPException(status_code=404, detail="Opponent not found")
    game = await db.games.find_one({"_id": ObjectId(data.game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    pair_ids = sorted([user["id"], data.opponent_user_id])
    existing = await db.competitions.find_one({
        "game_id": data.game_id,
        "platform": data.platform.strip(),
        "$or": [
            {"player_a_id": pair_ids[0], "player_b_id": pair_ids[1]},
            {"player_a_id": pair_ids[1], "player_b_id": pair_ids[0]},
        ],
        "status": "active",
    })
    if existing:
        raise HTTPException(status_code=400, detail="A competition with this player on this game/platform already exists")

    doc = {
        "id": str(uuid.uuid4()),
        "player_a_id": user["id"],
        "player_b_id": data.opponent_user_id,
        "game_id": data.game_id,
        "platform": data.platform.strip(),
        "stake_per_match": data.stake_per_match,
        "wins_a": 0,
        "wins_b": 0,
        "total_matches": 0,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.competitions.insert_one(doc)
    return await competition_to_dict(doc)


@api_router.get("/competitions")
async def list_competitions(user: dict = Depends(get_current_user)):
    cursor = db.competitions.find({
        "$or": [{"player_a_id": user["id"]}, {"player_b_id": user["id"]}]
    }).sort("created_at", -1)
    items = await cursor.to_list(500)
    return [await competition_to_dict(c) for c in items]


@api_router.get("/competitions/{comp_id}")
async def get_competition(comp_id: str, user: dict = Depends(get_current_user)):
    comp = await db.competitions.find_one({"id": comp_id})
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")
    if user["id"] not in (comp["player_a_id"], comp["player_b_id"]):
        raise HTTPException(status_code=403, detail="Not a participant")
    matches = await db.competition_matches.find({"competition_id": comp_id}).sort("created_at", -1).to_list(500)
    base = await competition_to_dict(comp)
    base["matches"] = [
        {
            "id": m["id"],
            "winner_user_id": m["winner_user_id"],
            "logged_by_id": m["logged_by_id"],
            "status": m["status"],
            "stake_amount": m["stake_amount"],
            "notes": m.get("notes"),
            "created_at": m["created_at"],
            "resolved_at": m.get("resolved_at"),
        } for m in matches
    ]
    return base


@api_router.post("/competitions/{comp_id}/log-match")
async def log_competition_match(comp_id: str, data: CompetitionMatchLog, user: dict = Depends(get_current_user)):
    """Player logs a match result (claims a winner). Goes to pending_confirmation
    until the opponent confirms. No money moves until confirmation."""
    comp = await db.competitions.find_one({"id": comp_id})
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")
    if user["id"] not in (comp["player_a_id"], comp["player_b_id"]):
        raise HTTPException(status_code=403, detail="Not a participant")
    if comp.get("status") != "active":
        raise HTTPException(status_code=400, detail="Competition is not active")
    if data.winner_user_id not in (comp["player_a_id"], comp["player_b_id"]):
        raise HTTPException(status_code=400, detail="Winner must be one of the two players")

    pending = await db.competition_matches.find_one({"competition_id": comp_id, "status": "pending_confirmation"})
    if pending:
        raise HTTPException(status_code=400, detail="There's already a match awaiting confirmation")

    match_doc = {
        "id": str(uuid.uuid4()),
        "competition_id": comp_id,
        "winner_user_id": data.winner_user_id,
        "logged_by_id": user["id"],
        "status": "pending_confirmation",
        "stake_amount": comp["stake_per_match"],
        "notes": (data.notes or "").strip()[:500],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.competition_matches.insert_one(match_doc)
    return {"id": match_doc["id"], "status": match_doc["status"]}


@api_router.post("/competitions/{comp_id}/matches/{match_id}/confirm")
async def confirm_competition_match(comp_id: str, match_id: str, user: dict = Depends(get_current_user)):
    """Opponent confirms the logged match. Stakes transfer from loser to winner."""
    comp = await db.competitions.find_one({"id": comp_id})
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")
    if user["id"] not in (comp["player_a_id"], comp["player_b_id"]):
        raise HTTPException(status_code=403, detail="Not a participant")

    match = await db.competition_matches.find_one({"id": match_id, "competition_id": comp_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match["status"] != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Match is not pending confirmation")
    if match["logged_by_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="The opponent must confirm, not the player who logged it")

    winner_id = match["winner_user_id"]
    loser_id = comp["player_b_id"] if winner_id == comp["player_a_id"] else comp["player_a_id"]
    stake = match["stake_amount"]

    loser = await db.users.find_one({"_id": ObjectId(loser_id)})
    if (loser.get("wallet_balance", 0.0) or 0.0) < stake:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance for {loser['username']} (needs {stake} CR). Cannot confirm — please dispute or have them top up."
        )

    await db.users.update_one({"_id": ObjectId(loser_id)}, {"$inc": {"wallet_balance": -stake}})
    await db.users.update_one({"_id": ObjectId(winner_id)}, {"$inc": {"wallet_balance": stake}})
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.wallet_transactions.insert_many([
        {"user_id": loser_id, "amount": -stake, "type": "debit",
         "reference_type": "competition_match_loss", "reference_id": match_id, "timestamp": now_iso},
        {"user_id": winner_id, "amount": stake, "type": "credit",
         "reference_type": "competition_match_win", "reference_id": match_id, "timestamp": now_iso},
    ])

    inc = {"total_matches": 1}
    if winner_id == comp["player_a_id"]:
        inc["wins_a"] = 1
    else:
        inc["wins_b"] = 1
    await db.competitions.update_one({"id": comp_id}, {"$inc": inc})

    await db.users.update_one({"_id": ObjectId(winner_id)}, {"$inc": {"total_wins": 1}})
    await db.users.update_one({"_id": ObjectId(loser_id)}, {"$inc": {"total_losses": 1}})

    await db.competition_matches.update_one(
        {"id": match_id},
        {"$set": {"status": "confirmed", "resolved_at": now_iso}}
    )
    try:
        await recompute_user_dispute_status(comp["player_a_id"])
        await recompute_user_dispute_status(comp["player_b_id"])
    except Exception as e:
        logger.warning(f"dispute recompute failed: {e}")
    return {"status": "confirmed"}


@api_router.post("/competitions/{comp_id}/matches/{match_id}/dispute")
async def dispute_competition_match(comp_id: str, match_id: str, user: dict = Depends(get_current_user)):
    """Opponent rejects the claim — match is cancelled (no money moves)."""
    comp = await db.competitions.find_one({"id": comp_id})
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")
    if user["id"] not in (comp["player_a_id"], comp["player_b_id"]):
        raise HTTPException(status_code=403, detail="Not a participant")
    match = await db.competition_matches.find_one({"id": match_id, "competition_id": comp_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match["status"] != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Match is not pending confirmation")
    if match["logged_by_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="The opponent must dispute, not the player who logged it")
    adv = await compute_competition_latency_advantage(comp_id, match_id=match_id)
    await db.competition_matches.update_one(
        {"id": match_id},
        {"$set": {
            "status": "cancelled",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "latency_advantage": adv,
        }}
    )
    admin_email = os.environ.get("DISPUTE_ALERT_EMAIL", "").strip()
    if admin_email:
        opener = await db.users.find_one({"_id": ObjectId(user["id"])})
        logger_user = await db.users.find_one({"_id": ObjectId(match["logged_by_id"])})
        game = await db.games.find_one({"_id": ObjectId(comp["game_id"])}) if comp.get("game_id") else None
        claimed_winner = await db.users.find_one({"_id": ObjectId(match["winner_user_id"])})
        app_url = os.environ.get("FRONTEND_URL", "https://gomofos.com")
        adv_ctx = None
        if adv and adv.get("advantage_user_id"):
            adv_u = await db.users.find_one({"_id": ObjectId(adv["advantage_user_id"])})
            adv_ctx = (f"Latency tie-breaker: {adv_u['username'] if adv_u else 'unknown'} had the better connection "
                       f"(see breakdown in dispute review)")
        asyncio.create_task(send_dispute_admin_alert(
            admin_email=admin_email,
            dispute_type="Head-to-Head Competition Match",
            opener_username=(opener.get("username", "Unknown") if opener else "Unknown"),
            opener_email=(opener.get("email", "") if opener else ""),
            opponent_username=(logger_user.get("username", "Unknown") if logger_user else "Unknown"),
            opponent_email=(logger_user.get("email", "") if logger_user else ""),
            game_name=(game["name"] if game else "Unknown"),
            platform=comp.get("platform", ""),
            stake_amount=float(match.get("stake_amount", 0)),
            dispute_id=f"comp:{comp_id} match:{match_id}",
            review_url=f"{app_url.rstrip('/')}/admin/disputes",
            extra_context=(
                f"{logger_user.get('username', '?') if logger_user else '?'} claimed "
                f"{claimed_winner.get('username', '?') if claimed_winner else '?'} won. "
                f"{opener.get('username', '?') if opener else '?'} rejected the claim — "
                f"no money has moved yet. Notes: {match.get('notes') or '(none)'}. "
                f"{adv_ctx or ''}"
            ),
        ))
    try:
        await recompute_user_dispute_status(comp["player_a_id"])
        await recompute_user_dispute_status(comp["player_b_id"])
    except Exception as e:
        logger.warning(f"dispute recompute failed: {e}")
    return {"status": "cancelled", "latency_advantage": adv, "dispute_threshold_warning": True, "hold_threshold_pct": int(DISPUTE_HOLD_THRESHOLD*100)}


@api_router.post("/competitions/{comp_id}/latency")
async def record_competition_latency(
    comp_id: str,
    latency_ms: float,
    match_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Record a single latency sample during a head-to-head match."""
    comp = await db.competitions.find_one({"id": comp_id})
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")
    if user["id"] not in (comp["player_a_id"], comp["player_b_id"]):
        raise HTTPException(status_code=403, detail="Only competition participants can record latency")
    doc = {
        "competition_id": comp_id,
        "user_id": user["id"],
        "latency_ms": float(latency_ms),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
    }
    if match_id:
        doc["match_id"] = match_id
    await db.competition_latency.insert_one(doc)
    return {"recorded": True}


@api_router.get("/competitions/{comp_id}/latency-advantage")
async def get_competition_latency_advantage(
    comp_id: str,
    match_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Tie-breaker payload for a head-to-head competition (whole comp or a specific match)."""
    comp = await db.competitions.find_one({"id": comp_id})
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    is_participant = user["id"] in (comp["player_a_id"], comp["player_b_id"])
    is_admin = user_doc and user_doc.get("role") == "admin"
    if not is_participant and not is_admin:
        raise HTTPException(status_code=403, detail="Only participants or admins can view this")
    return await compute_competition_latency_advantage(comp_id, match_id=match_id)
