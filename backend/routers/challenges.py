"""Challenges (1v1 private tournament invites): create, decline (link + auth), incoming."""
import asyncio
import os
from datetime import datetime, timezone

import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse

from core import (
    api_router, app, db, logger, JWT_ALGORITHM,
    get_current_user, get_jwt_secret, create_decline_token,
)
from email_service import send_match_invite
from models import ChallengeCreate


@api_router.post("/challenges")
async def create_challenge(challenge: ChallengeCreate, user: dict = Depends(get_current_user)):
    """Create a private 1v1 tournament invite for a specific opponent."""
    if challenge.opponent_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot challenge yourself")
    if challenge.stake_amount <= 0:
        raise HTTPException(status_code=400, detail="Stake amount must be greater than 0")

    opponent = await db.users.find_one({"_id": ObjectId(challenge.opponent_user_id)})
    if not opponent:
        raise HTTPException(status_code=404, detail="Opponent not found")

    game = await db.games.find_one({"_id": ObjectId(challenge.game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    user_data = await db.users.find_one({"_id": ObjectId(user["id"])})
    if user_data.get("wallet_balance", 0.0) < challenge.stake_amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -challenge.stake_amount}})

    tournament_doc = {
        "game_id": challenge.game_id,
        "creator_id": user["id"],
        "stake_amount": challenge.stake_amount,
        "status": "open",
        "max_players": 2,
        "current_players": 1,
        "winner_id": None,
        "start_time": challenge.start_time,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_private": True,
        "invited_user_ids": [challenge.opponent_user_id],
    }
    result = await db.tournaments.insert_one(tournament_doc)

    await db.tournament_participants.insert_one({
        "tournament_id": str(result.inserted_id),
        "user_id": user["id"],
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "result_status": "pending"
    })

    if opponent.get("email"):
        decline_token = create_decline_token(str(result.inserted_id), str(opponent["_id"]))
        asyncio.create_task(send_match_invite(
            to_email=opponent["email"],
            opponent_username=opponent.get("username", "Mofo"),
            challenger_username=user_data.get("username", "A challenger"),
            game_name=game.get("name", "the game"),
            stake_amount=float(challenge.stake_amount),
            tournament_id=str(result.inserted_id),
            app_url=os.environ.get("FRONTEND_URL", "https://gomofos.com"),
            decline_token=decline_token,
        ))

    return {
        "tournament_id": str(result.inserted_id),
        "opponent_username": opponent["username"],
        "stake_amount": challenge.stake_amount,
        "message": f"Challenge sent to {opponent['username']}"
    }


async def _decline_challenge_core(token: str) -> dict:
    """Validate the decline token, mark the challenge declined, refund both stakes."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {"status": "expired", "title": "Link expired", "message": "This decline link is no longer valid.", "tournament_id": None}
    except jwt.InvalidTokenError:
        return {"status": "invalid", "title": "Invalid link", "message": "This decline link is malformed.", "tournament_id": None}

    if payload.get("type") != "decline_challenge":
        return {"status": "invalid", "title": "Invalid link", "message": "This link is not authorised to decline a challenge.", "tournament_id": None}

    tournament_id = payload.get("tid")
    invitee_id = payload.get("uid")

    try:
        tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    except Exception:
        tournament = None
    if not tournament:
        return {"status": "invalid", "title": "Challenge not found", "message": "We couldn't find that challenge — it may have been deleted.", "tournament_id": tournament_id}

    if str(invitee_id) not in (tournament.get("invited_user_ids") or []):
        return {"status": "invalid", "title": "Not your challenge", "message": "This decline link doesn't match the invited player.", "tournament_id": tournament_id}

    status = tournament.get("status")
    if status == "declined":
        return {"status": "already", "title": "Already declined", "message": "This challenge was already declined and stakes were refunded.", "tournament_id": tournament_id}
    if status != "open":
        return {"status": "started", "title": "Match already started", "message": f"This match is {status.replace('_', ' ')} — you can no longer decline it. Open the tournament page to continue.", "tournament_id": tournament_id}

    participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(100)
    stake = float(tournament.get("stake_amount", 0.0))
    refunded = []
    for p in participants:
        try:
            await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"wallet_balance": stake}})
            refunded.append(p["user_id"])
        except Exception as e:  # noqa: BLE001
            logger.error("Refund failed for user %s on tournament %s: %s", p.get("user_id"), tournament_id, e)

    await db.tournaments.update_one(
        {"_id": ObjectId(tournament_id)},
        {"$set": {
            "status": "declined",
            "declined_by": invitee_id,
            "declined_at": datetime.now(timezone.utc).isoformat(),
            "refunded_user_ids": refunded,
        }}
    )

    if len(refunded) == 1:
        msg = f"Got it — challenge declined and {stake:.0f} CR was refunded to the challenger."
    else:
        msg = f"Got it — challenge declined and {len(refunded) * stake:.0f} CR was refunded to {len(refunded)} players."

    return {
        "status": "ok",
        "title": "Challenge declined",
        "message": msg,
        "tournament_id": tournament_id,
    }


@app.get("/api/challenges/decline", response_class=HTMLResponse)
async def decline_challenge_via_link(token: str):
    """One-click decline endpoint linked from match-invite emails."""
    result = await _decline_challenge_core(token)
    base = (os.environ.get("FRONTEND_URL", "https://gomofos.com")).rstrip("/")
    cta_url = f"{base}/tournament/{result['tournament_id']}" if result.get("tournament_id") else base
    color = "#22C55E" if result["status"] == "ok" else ("#F59E0B" if result["status"] in ("already",) else "#EF4444")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{result['title']} · Gomofos</title>
<style>
body{{margin:0;background:#0A0A0A;color:#fff;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}}
.card{{max-width:520px;width:100%;background:#141414;border:1px solid #262626;padding:40px;}}
.tag{{font-size:12px;letter-spacing:0.25em;color:#FF3B30;font-weight:bold;margin:0 0 16px 0;}}
h1{{margin:0 0 16px 0;font-size:28px;line-height:1.15;color:{color};font-weight:900;}}
p{{margin:0 0 24px 0;font-size:15px;line-height:1.6;color:#A3A3A3;}}
a.btn{{background:#FF3B30;color:#fff;text-decoration:none;font-weight:bold;letter-spacing:0.05em;padding:14px 28px;display:inline-block;}}
</style>
</head>
<body>
<div class="card">
<p class="tag">GAME ON MOFOS!</p>
<h1>{result['title']}</h1>
<p>{result['message']}</p>
<a class="btn" href="{cta_url}">{'OPEN GOMOFOS' if result['status'] != 'ok' else 'BACK TO GOMOFOS'}</a>
</div>
</body>
</html>"""
    return HTMLResponse(content=page)


@api_router.post("/challenges/{tournament_id}/decline")
async def decline_challenge_authenticated(tournament_id: str, user: dict = Depends(get_current_user)):
    """In-app decline by the invited player. Same effect as the email one-click link."""
    try:
        tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    except Exception:
        tournament = None
    if not tournament:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if user["id"] not in (tournament.get("invited_user_ids") or []):
        raise HTTPException(status_code=403, detail="Only the invited player can decline this challenge")

    token = create_decline_token(tournament_id, user["id"])
    result = await _decline_challenge_core(token)
    if result["status"] not in ("ok", "already"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@api_router.get("/challenges/incoming")
async def get_incoming_challenges(user: dict = Depends(get_current_user)):
    """Get private tournaments where current user is invited but hasn't joined yet."""
    tournaments = await db.tournaments.find({
        "is_private": True,
        "invited_user_ids": user["id"],
        "status": "open"
    }).to_list(100)

    results = []
    for t in tournaments:
        joined = await db.tournament_participants.find_one({"tournament_id": str(t["_id"]), "user_id": user["id"]})
        if joined:
            continue
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])})
        creator = await db.users.find_one({"_id": ObjectId(t["creator_id"])})
        results.append({
            "tournament_id": str(t["_id"]),
            "game_name": game["name"] if game else "Unknown",
            "game_platform": game["platform"] if game else "Unknown",
            "challenger_username": creator["username"] if creator else "Unknown",
            "stake_amount": t["stake_amount"],
            "start_time": t["start_time"],
            "created_at": t["created_at"],
        })
    return results
