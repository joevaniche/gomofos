"""Tournaments: CRUD, join, submit-result, complete, get-details, evidence, latency tracking, WS, share card."""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import jwt
from bson import ObjectId
from fastapi import Depends, File, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from core import (
    api_router, app, db, logger,
    get_current_user, APP_NAME, DISPUTE_HOLD_THRESHOLD,
)
from email_service import send_dispute_alert, send_dispute_admin_alert
from models import TournamentCreate, TournamentResponse
from services import (
    award_winner_and_close,
    cleanup_expired_tournaments,
    compute_latency_advantage,
    recompute_user_dispute_status,
    put_object,
    get_object,
    absolute_base_url,
)


@api_router.post("/tournaments", response_model=TournamentResponse)
async def create_tournament(tournament_data: TournamentCreate, user: dict = Depends(get_current_user)):
    if tournament_data.stake_amount <= 0:
        raise HTTPException(status_code=400, detail="Stake amount must be greater than 0")
    if not tournament_data.platform or not tournament_data.platform.strip():
        raise HTTPException(status_code=400, detail="Platform is required")

    game = await db.games.find_one({"_id": ObjectId(tournament_data.game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    user_data = await db.users.find_one({"_id": ObjectId(user["id"])})
    if user_data.get("wallet_balance", 0.0) < tournament_data.stake_amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -tournament_data.stake_amount}})

    tournament_doc = {
        "game_id": tournament_data.game_id,
        "platform": tournament_data.platform.strip(),
        "creator_id": user["id"],
        "stake_amount": tournament_data.stake_amount,
        "status": "open",
        "max_players": tournament_data.max_players,
        "current_players": 1,
        "winner_id": None,
        "start_time": tournament_data.start_time,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.tournaments.insert_one(tournament_doc)

    await db.tournament_participants.insert_one({
        "tournament_id": str(result.inserted_id),
        "user_id": user["id"],
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "result_status": "pending"
    })

    return TournamentResponse(
        id=str(result.inserted_id),
        game_id=tournament_data.game_id,
        game_name=game["name"],
        platform=tournament_doc["platform"],
        creator_id=user["id"],
        creator_username=user["username"],
        stake_amount=tournament_data.stake_amount,
        status="open",
        max_players=tournament_data.max_players,
        current_players=1,
        winner_id=None,
        start_time=tournament_data.start_time,
        created_at=tournament_doc["created_at"]
    )


@api_router.get("/tournaments", response_model=List[TournamentResponse])
async def get_tournaments(
    status: Optional[str] = None,
    game_id: Optional[str] = None,
    platform: Optional[str] = None,
    min_stake: Optional[float] = None,
    max_stake: Optional[float] = None,
    current: dict = Depends(get_current_user)
):
    await cleanup_expired_tournaments()
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if game_id:
        query["game_id"] = game_id
    if platform:
        query["platform"] = platform
    if min_stake is not None:
        query.setdefault("stake_amount", {})["$gte"] = min_stake
    if max_stake is not None:
        query.setdefault("stake_amount", {})["$lte"] = max_stake

    tournaments = await db.tournaments.find(query).sort("start_time", 1).to_list(1000)
    result = []

    for t in tournaments:
        if t.get("is_private"):
            if current["id"] != t["creator_id"] and current["id"] not in (t.get("invited_user_ids") or []):
                continue
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])})
        creator = await db.users.find_one({"_id": ObjectId(t["creator_id"])})
        result.append(TournamentResponse(
            id=str(t["_id"]),
            game_id=t["game_id"],
            game_name=game["name"] if game else "Unknown",
            platform=t.get("platform") or (game["platform"] if game else "Unknown"),
            creator_id=t["creator_id"],
            creator_username=creator["username"] if creator else "Unknown",
            stake_amount=t["stake_amount"],
            status=t["status"],
            max_players=t["max_players"],
            current_players=t["current_players"],
            winner_id=t.get("winner_id"),
            start_time=t["start_time"],
            created_at=t["created_at"]
        ))

    return result


@api_router.get("/tournaments/mine", response_model=List[TournamentResponse])
async def get_my_tournaments(current: dict = Depends(get_current_user)):
    """All non-completed tournaments where the current user is creator or participant."""
    await cleanup_expired_tournaments()
    parts = await db.tournament_participants.find({"user_id": current["id"]}).to_list(2000)
    tournament_ids = list({p["tournament_id"] for p in parts})
    object_ids = [ObjectId(tid) for tid in tournament_ids]
    if not object_ids:
        return []
    tournaments = await db.tournaments.find({
        "_id": {"$in": object_ids},
        "status": {"$in": ["open", "in_progress", "pending_confirmation", "disputed"]}
    }).sort("created_at", -1).to_list(1000)
    result = []
    for t in tournaments:
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])})
        creator = await db.users.find_one({"_id": ObjectId(t["creator_id"])})
        result.append(TournamentResponse(
            id=str(t["_id"]),
            game_id=t["game_id"],
            game_name=game["name"] if game else "Unknown",
            platform=t.get("platform") or (game["platform"] if game else "Unknown"),
            creator_id=t["creator_id"],
            creator_username=creator["username"] if creator else "Unknown",
            stake_amount=t["stake_amount"],
            status=t["status"],
            max_players=t["max_players"],
            current_players=t["current_players"],
            winner_id=t.get("winner_id"),
            start_time=t["start_time"],
            created_at=t["created_at"]
        ))
    return result


@api_router.post("/tournaments/{tournament_id}/join")
async def join_tournament(tournament_id: str, user: dict = Depends(get_current_user)):
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if tournament["status"] != "open":
        raise HTTPException(status_code=400, detail="Tournament is not open")

    if tournament["current_players"] >= tournament["max_players"]:
        raise HTTPException(status_code=400, detail="Tournament is full")

    if tournament.get("is_private"):
        if user["id"] != tournament["creator_id"] and user["id"] not in (tournament.get("invited_user_ids") or []):
            raise HTTPException(status_code=403, detail="This is a private tournament — you must be invited")

    existing = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already joined")

    user_data = await db.users.find_one({"_id": ObjectId(user["id"])})
    if user_data.get("wallet_balance", 0.0) < tournament["stake_amount"]:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")

    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -tournament["stake_amount"]}})

    await db.tournament_participants.insert_one({
        "tournament_id": tournament_id,
        "user_id": user["id"],
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "result_status": "pending"
    })

    new_count = tournament["current_players"] + 1
    update_fields = {"current_players": new_count}
    if new_count >= tournament["max_players"]:
        update_fields["status"] = "in_progress"
        update_fields["started_at"] = datetime.now(timezone.utc).isoformat()
    await db.tournaments.update_one({"_id": ObjectId(tournament_id)}, {"$set": update_fields})

    return {"message": "Joined tournament successfully"}


@api_router.post("/tournaments/{tournament_id}/submit-result")
async def submit_result(tournament_id: str, claimed_winner_id: str, user: dict = Depends(get_current_user)):
    """Each participant submits who they believe won. When all participants submit, the system checks for agreement."""
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    if tournament["status"] not in ("in_progress", "pending_confirmation"):
        raise HTTPException(status_code=400, detail="Tournament is not awaiting results")

    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    if not participant:
        raise HTTPException(status_code=403, detail="Only participants can submit results")

    winner_check = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": claimed_winner_id})
    if not winner_check:
        raise HTTPException(status_code=400, detail="Claimed winner must be a tournament participant")

    await db.tournament_participants.update_one(
        {"tournament_id": tournament_id, "user_id": user["id"]},
        {"$set": {"claimed_winner_id": claimed_winner_id, "result_submitted_at": datetime.now(timezone.utc).isoformat()}}
    )

    if tournament["status"] == "in_progress":
        await db.tournaments.update_one({"_id": ObjectId(tournament_id)}, {"$set": {"status": "pending_confirmation"}})

    all_participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(1000)
    submitted = [p for p in all_participants if p.get("claimed_winner_id")]

    if len(submitted) < len(all_participants):
        return {"message": "Result submitted, waiting for other player(s)", "status": "pending_confirmation"}

    claims = set(p["claimed_winner_id"] for p in submitted)
    if len(claims) == 1:
        winner_id = claims.pop()
        winner_amount = await award_winner_and_close(tournament_id, winner_id, "auto_agreement")
        for p in all_participants:
            try:
                await recompute_user_dispute_status(p["user_id"])
            except Exception as e:
                logger.warning(f"dispute recompute failed: {e}")
        return {"message": "Tournament completed (all players agreed)", "status": "completed", "winner_id": winner_id, "winner_amount": winner_amount}
    else:
        advantage = await compute_latency_advantage(tournament_id)
        await db.tournaments.update_one(
            {"_id": ObjectId(tournament_id)},
            {"$set": {
                "status": "disputed",
                "disputed_at": datetime.now(timezone.utc).isoformat(),
                "latency_advantage": advantage,
            }}
        )
        opener_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
        opener_username = opener_doc.get("username", "An opponent") if opener_doc else "An opponent"
        opener_email = opener_doc.get("email", "") if opener_doc else ""
        game = await db.games.find_one({"_id": ObjectId(tournament["game_id"])}) if tournament.get("game_id") else None
        game_name = game["name"] if game else "your match"
        platform_str = tournament.get("platform") or (game["platform"] if game else "")
        pot = float(tournament.get("stake_amount", 0)) * len(all_participants)
        app_url = os.environ.get("FRONTEND_URL", "https://gomofos.com")
        adv_ctx = None
        if advantage and advantage.get("user_id"):
            adv_user = await db.users.find_one({"_id": ObjectId(advantage["user_id"])})
            adv_ctx = (f"Latency tie-breaker advantage: {adv_user['username'] if adv_user else 'unknown'} "
                       f"(avg {advantage.get('avg_ms','?')}ms — better than threshold)")
        first_opponent_username = ""
        first_opponent_email = ""
        for p in all_participants:
            if p["user_id"] == user["id"]:
                continue
            opponent_doc = await db.users.find_one({"_id": ObjectId(p["user_id"])})
            if opponent_doc and opponent_doc.get("email"):
                if not first_opponent_username:
                    first_opponent_username = opponent_doc.get("username", "Mofo")
                    first_opponent_email = opponent_doc.get("email", "")
                asyncio.create_task(send_dispute_alert(
                    to_email=opponent_doc["email"],
                    opponent_username=opponent_doc.get("username", "Mofo"),
                    opener_username=opener_username,
                    game_name=game_name,
                    stake_amount=pot,
                    tournament_id=tournament_id,
                    app_url=app_url,
                ))
        admin_email = os.environ.get("DISPUTE_ALERT_EMAIL", "").strip()
        if admin_email:
            asyncio.create_task(send_dispute_admin_alert(
                admin_email=admin_email,
                dispute_type="Tournament",
                opener_username=opener_username,
                opener_email=opener_email,
                opponent_username=first_opponent_username or "(multiple opponents)",
                opponent_email=first_opponent_email,
                game_name=game_name,
                platform=platform_str,
                stake_amount=pot,
                dispute_id=tournament_id,
                review_url=f"{app_url.rstrip('/')}/tournament/{tournament_id}",
                extra_context=adv_ctx,
            ))
        for p in all_participants:
            try:
                await recompute_user_dispute_status(p["user_id"])
            except Exception as e:
                logger.warning(f"dispute recompute failed: {e}")
        return {"message": "Players disagreed on winner — dispute created", "status": "disputed", "latency_advantage": advantage, "dispute_threshold_warning": True, "hold_threshold_pct": int(DISPUTE_HOLD_THRESHOLD*100)}


@api_router.post("/tournaments/{tournament_id}/complete")
async def complete_tournament(tournament_id: str, winner_user_id: str, user: dict = Depends(get_current_user)):
    """Legacy creator-decides endpoint, kept for admin dispute resolution."""
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    is_admin = user_doc.get("role") == "admin"

    if not is_admin and tournament["creator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only creator or admin can complete tournament")

    if tournament["status"] == "completed":
        raise HTTPException(status_code=400, detail="Tournament already completed")

    winner_participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": winner_user_id})
    if not winner_participant:
        raise HTTPException(status_code=400, detail="Winner must be a tournament participant")

    resolution = "admin_resolved" if is_admin else "creator_decided"
    winner_amount = await award_winner_and_close(tournament_id, winner_user_id, resolution)

    return {"message": "Tournament completed", "winner_amount": winner_amount}


@api_router.get("/tournaments/{tournament_id}")
async def get_tournament_details(tournament_id: str):
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    game = await db.games.find_one({"_id": ObjectId(tournament["game_id"])})
    creator = await db.users.find_one({"_id": ObjectId(tournament["creator_id"])})

    participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(1000)
    participant_list = []
    for p in participants:
        u = await db.users.find_one({"_id": ObjectId(p["user_id"])})
        participant_list.append({
            "user_id": p["user_id"],
            "username": u["username"] if u else "Unknown",
            "joined_at": p["joined_at"],
            "claimed_winner_id": p.get("claimed_winner_id"),
            "result_submitted_at": p.get("result_submitted_at"),
        })

    return {
        "id": str(tournament["_id"]),
        "game_id": tournament["game_id"],
        "game_name": game["name"] if game else "Unknown",
        "platform": tournament.get("platform") or (game["platform"] if game else "Unknown"),
        "creator_id": tournament["creator_id"],
        "creator_username": creator["username"] if creator else "Unknown",
        "stake_amount": tournament["stake_amount"],
        "status": tournament["status"],
        "max_players": tournament["max_players"],
        "current_players": tournament["current_players"],
        "winner_id": tournament.get("winner_id"),
        "start_time": tournament["start_time"],
        "started_at": tournament.get("started_at"),
        "disputed_at": tournament.get("disputed_at"),
        "completed_at": tournament.get("completed_at"),
        "resolution": tournament.get("resolution"),
        "created_at": tournament["created_at"],
        "participants": participant_list,
        "latency_advantage": tournament.get("latency_advantage"),
    }


# ============ EVIDENCE (Screenshots) ============
@api_router.post("/tournaments/{tournament_id}/evidence")
async def upload_evidence(tournament_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Upload a screenshot as evidence for a tournament (dispute resolution)."""
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    if not participant:
        raise HTTPException(status_code=403, detail="Only participants can upload evidence")

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files allowed (JPG, PNG, WEBP, GIF)")

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "png"
    path = f"{APP_NAME}/evidence/{tournament_id}/{uuid.uuid4()}.{ext}"

    result = put_object(path, data, file.content_type)

    evidence_doc = {
        "id": str(uuid.uuid4()),
        "tournament_id": tournament_id,
        "user_id": user["id"],
        "storage_path": result["path"],
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "original_filename": file.filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    await db.tournament_evidence.insert_one(evidence_doc)

    return {"id": evidence_doc["id"], "storage_path": result["path"], "uploaded_at": evidence_doc["uploaded_at"]}


@api_router.get("/tournaments/{tournament_id}/evidence")
async def list_evidence(tournament_id: str, user: dict = Depends(get_current_user)):
    """List all evidence for a tournament."""
    items = await db.tournament_evidence.find({"tournament_id": tournament_id}).to_list(100)
    result = []
    for item in items:
        uploader = await db.users.find_one({"_id": ObjectId(item["user_id"])})
        result.append({
            "id": item["id"],
            "user_id": item["user_id"],
            "username": uploader["username"] if uploader else "Unknown",
            "storage_path": item["storage_path"],
            "uploaded_at": item["uploaded_at"],
        })
    return result


@api_router.get("/evidence/{evidence_id}/download")
async def download_evidence(evidence_id: str, user: dict = Depends(get_current_user)):
    """Stream an evidence image."""
    item = await db.tournament_evidence.find_one({"id": evidence_id})
    if not item:
        raise HTTPException(status_code=404, detail="Evidence not found")
    data, content_type = get_object(item["storage_path"])
    return Response(content=data, media_type=item.get("content_type", content_type))


# ============ LATENCY ============
@api_router.post("/tournaments/{tournament_id}/latency")
async def record_latency(tournament_id: str, latency_ms: float, user: dict = Depends(get_current_user)):
    """Record a single latency sample for a player during a match (HTTP fallback)."""
    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    if not participant:
        raise HTTPException(status_code=403, detail="Only participants can record latency")

    await db.tournament_latency.insert_one({
        "tournament_id": tournament_id,
        "user_id": user["id"],
        "latency_ms": float(latency_ms),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"recorded": True}


@api_router.get("/tournaments/{tournament_id}/latency-advantage")
async def get_latency_advantage(tournament_id: str, user: dict = Depends(get_current_user)):
    """Return the per-tournament latency tie-breaker payload (used by admins reviewing disputes)."""
    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not participant and (not user_doc or user_doc.get("role") != "admin"):
        raise HTTPException(status_code=403, detail="Only participants or admins can view this")
    return await compute_latency_advantage(tournament_id)


@api_router.get("/tournaments/{tournament_id}/latency")
async def get_latency_history(tournament_id: str, user: dict = Depends(get_current_user)):
    """Get latency timeline for all participants of a tournament (for dispute review)."""
    samples = await db.tournament_latency.find({"tournament_id": tournament_id}).sort("timestamp", 1).to_list(10000)

    by_user: Dict[str, list] = {}
    for s in samples:
        by_user.setdefault(s["user_id"], []).append({"latency_ms": s["latency_ms"], "timestamp": s["timestamp"]})

    result = []
    for uid, points in by_user.items():
        u = await db.users.find_one({"_id": ObjectId(uid)})
        latencies = [p["latency_ms"] for p in points]
        result.append({
            "user_id": uid,
            "username": u["username"] if u else "Unknown",
            "sample_count": len(points),
            "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "max_ms": max(latencies) if latencies else 0,
            "min_ms": min(latencies) if latencies else 0,
            "samples": points,
        })
    return result


@app.websocket("/api/ws/latency")
async def latency_websocket(websocket: WebSocket, tournament_id: str, token: str):
    """Real-time latency ping endpoint. Client sends {ping: timestamp}; server immediately echoes and records latency."""
    await websocket.accept()

    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        user_id = payload["sub"]
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            await websocket.close(code=4401)
            return
    except Exception:
        await websocket.close(code=4401)
        return

    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user_id})
    if not participant:
        await websocket.close(code=4403)
        return

    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                client_ts = message.get("client_ts")
                await websocket.send_json({"type": "pong", "client_ts": client_ts, "server_ts": int(datetime.now(timezone.utc).timestamp() * 1000)})
            elif message.get("type") == "report":
                rtt = float(message.get("latency_ms", 0))
                if rtt > 0:
                    await db.tournament_latency.insert_one({
                        "tournament_id": tournament_id,
                        "user_id": user_id,
                        "latency_ms": rtt,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


# ============ TOURNAMENT SHARE CARD (OG meta for X/Twitter) ============
@app.get("/api/share/tournament/{tournament_id}", response_class=HTMLResponse)
async def tournament_share_card(tournament_id: str, reel: str = ""):
    """Public HTML page with Open Graph meta tags so X/Twitter can render a rich preview
    (with optional video preview) when a tournament result is shared."""
    try:
        t = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    except Exception:
        t = None
    if not t:
        return HTMLResponse("<h1>Tournament not found</h1>", status_code=404)

    game = await db.games.find_one({"_id": ObjectId(t["game_id"])}) if t.get("game_id") else None
    game_name = game["name"] if game else "the game"
    winner = None
    if t.get("winner_id"):
        try:
            winner = await db.users.find_one({"_id": ObjectId(t["winner_id"])})
        except Exception:
            winner = None
    winner_name = winner["username"] if winner else "A Mofo"
    participant_count = await db.tournament_participants.count_documents({"tournament_id": tournament_id})
    pot = float(t.get("stake_amount", 0)) * (participant_count or 2)

    title = f"{winner_name} won {pot:.0f} CR on Gomofos!"
    description = f"{winner_name} just took the pot playing {game_name} on GoMofos. Stake. Compete. Dominate."

    base = absolute_base_url().rstrip("/")
    page_url = f"{base}/api/share/tournament/{tournament_id}" + (f"?reel={reel}" if reel else "")
    image_url = f"{base}/gomofos-logo.png"
    redirect_url = f"{base}/tournament/{tournament_id}"

    video_meta = ""
    if reel:
        reel_doc = await db.highlight_reels.find_one({"id": reel, "is_public": True})
        if reel_doc:
            video_url = f"{base}/api/highlights/{reel}/stream"
            video_meta = f"""
    <meta property="og:video" content="{video_url}" />
    <meta property="og:video:secure_url" content="{video_url}" />
    <meta property="og:video:type" content="{reel_doc.get('content_type', 'video/mp4')}" />
    <meta property="og:video:width" content="1280" />
    <meta property="og:video:height" content="720" />
    <meta name="twitter:card" content="player" />
    <meta name="twitter:player" content="{video_url}" />
    <meta name="twitter:player:width" content="1280" />
    <meta name="twitter:player:height" content="720" />
    <meta name="twitter:player:stream" content="{video_url}" />
    <meta name="twitter:player:stream:content_type" content="{reel_doc.get('content_type', 'video/mp4')}" />
"""

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<meta property="og:type" content="website" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{description}" />
<meta property="og:url" content="{page_url}" />
<meta property="og:image" content="{image_url}" />
<meta property="og:site_name" content="GoMofos" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{description}" />
<meta name="twitter:image" content="{image_url}" />
{video_meta}
<meta http-equiv="refresh" content="2; url={redirect_url}" />
<style>body{{font-family:system-ui;background:#0A0A0A;color:#fff;text-align:center;padding:64px 24px;}}a{{color:#FF3B30;}}</style>
</head>
<body>
<h1>{title}</h1>
<p>{description}</p>
<p>Redirecting to the tournament... <a href="{redirect_url}">tap here if it doesn't load</a></p>
</body>
</html>"""
    return HTMLResponse(content=html)
