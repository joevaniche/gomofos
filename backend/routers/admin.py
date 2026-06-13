"""Admin: dispute listing/resolution, unhold, hard-deletes (users/tournaments/competitions)."""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import Depends, HTTPException

from core import api_router, db, get_current_user
from models import AdminDisputeResolution
from services import require_admin


@api_router.get("/admin/disputes")
async def list_admin_disputes(user: dict = Depends(get_current_user)):
    """List every open dispute across the platform — both tournament and head-to-head competition match disputes."""
    await require_admin(user)
    out = []

    tournaments = await db.tournaments.find({"status": "disputed"}).sort("disputed_at", -1).to_list(500)
    for t in tournaments:
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])}) if t.get("game_id") else None
        parts = await db.tournament_participants.find({"tournament_id": str(t["_id"])}).to_list(50)
        participants = []
        for p in parts:
            u = await db.users.find_one({"_id": ObjectId(p["user_id"])})
            participants.append({
                "user_id": p["user_id"],
                "username": u.get("username") if u else "Unknown",
                "email": u.get("email") if u else "",
                "claimed_winner_id": p.get("claimed_winner_id"),
            })
        out.append({
            "kind": "tournament",
            "id": str(t["_id"]),
            "game_id": t.get("game_id"),
            "game_name": game["name"] if game else "Unknown",
            "platform": t.get("platform") or (game.get("platform") if game else ""),
            "stake_amount": float(t.get("stake_amount", 0)) * len(parts),
            "per_player_stake": float(t.get("stake_amount", 0)),
            "participants": participants,
            "disputed_at": t.get("disputed_at"),
            "latency_advantage": t.get("latency_advantage"),
            "created_at": t.get("created_at"),
        })

    cancelled_matches = await db.competition_matches.find({
        "status": "cancelled",
        "admin_resolution": {"$exists": False},
    }).sort("resolved_at", -1).to_list(500)
    for m in cancelled_matches:
        comp = await db.competitions.find_one({"id": m["competition_id"]})
        if not comp:
            continue
        game = await db.games.find_one({"_id": ObjectId(comp["game_id"])}) if comp.get("game_id") else None
        player_a = await db.users.find_one({"_id": ObjectId(comp["player_a_id"])})
        player_b = await db.users.find_one({"_id": ObjectId(comp["player_b_id"])})
        claimed = await db.users.find_one({"_id": ObjectId(m["winner_user_id"])})
        logger_u = await db.users.find_one({"_id": ObjectId(m["logged_by_id"])})
        out.append({
            "kind": "competition_match",
            "id": m["id"],
            "competition_id": m["competition_id"],
            "game_id": comp.get("game_id"),
            "game_name": game["name"] if game else "Unknown",
            "platform": comp.get("platform"),
            "stake_amount": float(m.get("stake_amount", 0)),
            "participants": [
                {"user_id": comp["player_a_id"], "username": player_a.get("username") if player_a else "?", "email": player_a.get("email") if player_a else ""},
                {"user_id": comp["player_b_id"], "username": player_b.get("username") if player_b else "?", "email": player_b.get("email") if player_b else ""},
            ],
            "claimed_winner_id": m["winner_user_id"],
            "claimed_winner_username": claimed.get("username") if claimed else "?",
            "logged_by_id": m["logged_by_id"],
            "logged_by_username": logger_u.get("username") if logger_u else "?",
            "notes": m.get("notes"),
            "resolved_at": m.get("resolved_at"),
            "latency_advantage": m.get("latency_advantage"),
            "created_at": m.get("created_at"),
        })

    out.sort(key=lambda d: d.get("disputed_at") or d.get("resolved_at") or d.get("created_at") or "", reverse=True)
    return out


@api_router.post("/admin/disputes/resolve")
async def admin_resolve_dispute(payload: AdminDisputeResolution, user: dict = Depends(get_current_user)):
    """Admin closes a dispute. If winner_user_id is provided, the pot transfers to them.
    If it's left blank, the match/tournament is voided and all stakes are refunded."""
    await require_admin(user)
    now_iso = datetime.now(timezone.utc).isoformat()

    if payload.kind == "tournament":
        t = await db.tournaments.find_one({"_id": ObjectId(payload.id)})
        if not t:
            raise HTTPException(status_code=404, detail="Tournament not found")
        if t.get("status") not in ("disputed", "pending_confirmation", "in_progress"):
            raise HTTPException(status_code=400, detail=f"Tournament status '{t.get('status')}' cannot be admin-resolved")
        parts = await db.tournament_participants.find({"tournament_id": payload.id}).to_list(50)
        stake = float(t.get("stake_amount", 0))

        if payload.winner_user_id:
            if not any(p["user_id"] == payload.winner_user_id for p in parts):
                raise HTTPException(status_code=400, detail="Winner must be one of the participants")
            pot = stake * len(parts)
            await db.users.update_one({"_id": ObjectId(payload.winner_user_id)}, {"$inc": {"wallet_balance": pot, "total_wins": 1}})
            for p in parts:
                if p["user_id"] != payload.winner_user_id:
                    await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"total_losses": 1}})
            await db.wallet_transactions.insert_one({
                "user_id": payload.winner_user_id, "amount": pot, "type": "credit",
                "reference_type": "tournament_admin_resolved", "reference_id": payload.id, "timestamp": now_iso,
            })
            await db.tournaments.update_one(
                {"_id": ObjectId(payload.id)},
                {"$set": {
                    "status": "completed", "winner_id": payload.winner_user_id,
                    "completed_at": now_iso, "resolution": "admin_resolved",
                    "resolved_by_admin_id": user["id"], "admin_note": payload.note,
                }}
            )
            return {"status": "completed", "winner_id": payload.winner_user_id, "pot": pot}
        else:
            for p in parts:
                await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"wallet_balance": stake}})
                await db.wallet_transactions.insert_one({
                    "user_id": p["user_id"], "amount": stake, "type": "credit",
                    "reference_type": "tournament_admin_voided", "reference_id": payload.id, "timestamp": now_iso,
                })
            await db.tournaments.update_one(
                {"_id": ObjectId(payload.id)},
                {"$set": {
                    "status": "voided", "completed_at": now_iso, "resolution": "admin_voided",
                    "resolved_by_admin_id": user["id"], "admin_note": payload.note,
                }}
            )
            return {"status": "voided", "refunded_per_player": stake}

    elif payload.kind == "competition_match":
        if not payload.competition_id:
            raise HTTPException(status_code=400, detail="competition_id is required for competition_match disputes")
        comp = await db.competitions.find_one({"id": payload.competition_id})
        if not comp:
            raise HTTPException(status_code=404, detail="Competition not found")
        m = await db.competition_matches.find_one({"id": payload.id, "competition_id": payload.competition_id})
        if not m:
            raise HTTPException(status_code=404, detail="Match not found")
        if m.get("admin_resolution"):
            raise HTTPException(status_code=400, detail="Match already admin-resolved")
        stake = float(m.get("stake_amount", 0))

        if payload.winner_user_id:
            if payload.winner_user_id not in (comp["player_a_id"], comp["player_b_id"]):
                raise HTTPException(status_code=400, detail="Winner must be one of the two players")
            loser_id = comp["player_b_id"] if payload.winner_user_id == comp["player_a_id"] else comp["player_a_id"]
            loser = await db.users.find_one({"_id": ObjectId(loser_id)})
            if (loser.get("wallet_balance", 0.0) or 0.0) < stake:
                raise HTTPException(status_code=400,
                    detail=f"Cannot transfer pot — {loser.get('username','loser')} has insufficient balance ({stake} CR needed)")
            await db.users.update_one({"_id": ObjectId(loser_id)}, {"$inc": {"wallet_balance": -stake, "total_losses": 1}})
            await db.users.update_one({"_id": ObjectId(payload.winner_user_id)}, {"$inc": {"wallet_balance": stake, "total_wins": 1}})
            await db.wallet_transactions.insert_many([
                {"user_id": loser_id, "amount": -stake, "type": "debit",
                 "reference_type": "competition_admin_resolved_loss", "reference_id": payload.id, "timestamp": now_iso},
                {"user_id": payload.winner_user_id, "amount": stake, "type": "credit",
                 "reference_type": "competition_admin_resolved_win", "reference_id": payload.id, "timestamp": now_iso},
            ])
            inc = {"total_matches": 1}
            if payload.winner_user_id == comp["player_a_id"]:
                inc["wins_a"] = 1
            else:
                inc["wins_b"] = 1
            await db.competitions.update_one({"id": payload.competition_id}, {"$inc": inc})
            await db.competition_matches.update_one(
                {"id": payload.id},
                {"$set": {
                    "status": "confirmed", "resolved_at": now_iso,
                    "winner_user_id": payload.winner_user_id,
                    "admin_resolution": "winner", "resolved_by_admin_id": user["id"],
                    "admin_note": payload.note,
                }}
            )
            return {"status": "confirmed", "winner_id": payload.winner_user_id, "transferred": stake}
        else:
            await db.competition_matches.update_one(
                {"id": payload.id},
                {"$set": {
                    "status": "voided", "resolved_at": now_iso,
                    "admin_resolution": "void", "resolved_by_admin_id": user["id"],
                    "admin_note": payload.note,
                }}
            )
            return {"status": "voided"}

    raise HTTPException(status_code=400, detail=f"Unknown dispute kind: {payload.kind}")


@api_router.post("/admin/users/{user_id}/unhold")
async def admin_release_hold(user_id: str, user: dict = Depends(get_current_user)):
    await require_admin(user)
    await db.users.update_one({"_id": ObjectId(user_id)},
        {"$set": {"status": "active"}, "$unset": {"on_hold_reason": "", "on_hold_at": ""}})
    return {"status": "active"}


# ============ ADMIN DELETE ============
@api_router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user: dict = Depends(get_current_user)):
    """Hard delete a user account + every record they're attached to. Irreversible."""
    await require_admin(user)
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You can't delete your own account from here")
    try:
        target = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.tournament_participants.delete_many({"user_id": user_id})
    await db.competition_matches.delete_many({"$or": [{"logged_by_id": user_id}, {"winner_user_id": user_id}]})
    await db.competitions.delete_many({"$or": [{"player_a_id": user_id}, {"player_b_id": user_id}]})
    await db.user_prizes.delete_many({"user_id": user_id})
    await db.wallet_transactions.delete_many({"user_id": user_id})
    await db.highlight_reels.delete_many({"user_id": user_id})
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"deleted": user_id}


@api_router.delete("/admin/tournaments/{tournament_id}")
async def admin_delete_tournament(tournament_id: str, user: dict = Depends(get_current_user)):
    """Refund every participant and hard-delete a tournament."""
    await require_admin(user)
    try:
        t = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")
    parts = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(50)
    stake = float(t.get("stake_amount", 0))
    now_iso = datetime.now(timezone.utc).isoformat()
    refunded = 0
    if t.get("status") not in ("completed", "voided"):
        for p in parts:
            await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"wallet_balance": stake}})
            await db.wallet_transactions.insert_one({
                "user_id": p["user_id"], "amount": stake, "type": "credit",
                "reference_type": "tournament_admin_deleted", "reference_id": tournament_id,
                "timestamp": now_iso,
            })
            refunded += 1
    await db.tournament_participants.delete_many({"tournament_id": tournament_id})
    await db.tournaments.delete_one({"_id": ObjectId(tournament_id)})
    return {"deleted": tournament_id, "refunded_players": refunded}


@api_router.delete("/admin/competitions/{comp_id}")
async def admin_delete_competition(comp_id: str, user: dict = Depends(get_current_user)):
    await require_admin(user)
    c = await db.competitions.find_one({"id": comp_id})
    if not c:
        raise HTTPException(status_code=404, detail="Competition not found")
    await db.competition_matches.delete_many({"competition_id": comp_id})
    await db.competition_latency.delete_many({"competition_id": comp_id})
    await db.competitions.delete_one({"id": comp_id})
    return {"deleted": comp_id}
