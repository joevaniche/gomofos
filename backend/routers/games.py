"""Game catalog + per-game leaderboard."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException

from core import api_router, db, get_current_user
from models import GameCreate, GameResponse
from services import require_admin


@api_router.post("/games", response_model=GameResponse)
async def create_game(game_data: GameCreate, user: dict = Depends(get_current_user)):
    game_doc = {
        "name": game_data.name,
        "platform": game_data.platform,
        "image_url": game_data.image_url,
        "category": game_data.category,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.games.insert_one(game_doc)
    return GameResponse(
        id=str(result.inserted_id),
        name=game_doc["name"],
        platform=game_doc["platform"],
        image_url=game_doc["image_url"],
        category=game_doc.get("category"),
        created_at=game_doc["created_at"]
    )


@api_router.get("/games", response_model=List[GameResponse])
async def get_games(q: Optional[str] = None, category: Optional[str] = None):
    query: Dict[str, Any] = {}
    if q:
        import re
        q_safe = re.escape(q)
        query["name"] = {"$regex": q_safe, "$options": "i"}
    if category:
        query["category"] = category
    games = await db.games.find(query).sort("name", 1).to_list(2000)
    return [GameResponse(
        id=str(g["_id"]),
        name=g["name"],
        platform=g["platform"],
        image_url=g.get("image_url"),
        category=g.get("category"),
        created_at=g["created_at"]
    ) for g in games]


@api_router.get("/games/categories")
async def list_game_categories():
    """Distinct list of game categories currently in the catalog."""
    cats = await db.games.distinct("category")
    return sorted([c for c in cats if c])


@api_router.post("/admin/seed-games")
async def admin_seed_games(user: dict = Depends(get_current_user)):
    """Admin-only: bulk-insert the curated top games catalog. Skips games already present (matched by name, case-insensitive)."""
    await require_admin(user)

    from games_data import TOP_GAMES

    existing = await db.games.find({}, {"name": 1}).to_list(5000)
    existing_lower = {g["name"].lower() for g in existing}

    inserted = 0
    skipped = 0
    docs_to_insert = []
    now = datetime.now(timezone.utc).isoformat()

    for g in TOP_GAMES:
        if g["name"].lower() in existing_lower:
            skipped += 1
            continue
        docs_to_insert.append({
            "name": g["name"],
            "platform": g["platform"],
            "image_url": g.get("image_url"),
            "category": g.get("category"),
            "created_by": user["id"],
            "created_at": now,
        })
        existing_lower.add(g["name"].lower())

    if docs_to_insert:
        result = await db.games.insert_many(docs_to_insert)
        inserted = len(result.inserted_ids)

    return {
        "inserted": inserted,
        "skipped": skipped,
        "total_in_catalog": len(TOP_GAMES),
        "message": f"Added {inserted} new games. Skipped {skipped} duplicates."
    }


@api_router.get("/games/{game_id}/leaderboard")
async def get_game_leaderboard(game_id: str, current: dict = Depends(get_current_user)):
    """Per-game leaderboard. Counts every completed tournament + confirmed h2h match
    on this specific game and ranks players by wins (tie-break: net credits)."""
    try:
        game = await db.games.find_one({"_id": ObjectId(game_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Game not found")
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    stats: Dict[str, Dict[str, Any]] = {}
    def _row(uid: str):
        if uid not in stats:
            stats[uid] = {"user_id": uid, "wins": 0, "losses": 0, "net_credits": 0.0}
        return stats[uid]

    tournaments = await db.tournaments.find({"game_id": game_id, "status": "completed"}).to_list(2000)
    for t in tournaments:
        parts = await db.tournament_participants.find({"tournament_id": str(t["_id"])}).to_list(50)
        stake = float(t.get("stake_amount", 0))
        n_players = len(parts)
        winner = t.get("winner_id")
        for p in parts:
            r = _row(p["user_id"])
            if p["user_id"] == winner:
                r["wins"] += 1
                r["net_credits"] += stake * (n_players - 1)
            else:
                r["losses"] += 1
                r["net_credits"] -= stake

    comps = await db.competitions.find({"game_id": game_id}).to_list(2000)
    for c in comps:
        matches = await db.competition_matches.find({"competition_id": c["id"], "status": "confirmed"}).to_list(5000)
        for m in matches:
            stake = float(m.get("stake_amount", 0))
            winner = m["winner_user_id"]
            loser = c["player_b_id"] if winner == c["player_a_id"] else c["player_a_id"]
            rw = _row(winner); rw["wins"] += 1; rw["net_credits"] += stake
            rl = _row(loser); rl["losses"] += 1; rl["net_credits"] -= stake

    rows = []
    for uid, r in stats.items():
        u = await db.users.find_one({"_id": ObjectId(uid)})
        if not u:
            continue
        equipped_thumbs = []
        equipped = (u.get("equipped_prizes") or {}) if isinstance(u.get("equipped_prizes"), dict) else {}
        for inv_id in set(equipped.values()):
            inv = await db.user_prizes.find_one({"id": inv_id, "user_id": uid})
            if not inv: continue
            prize = await db.prizes.find_one({"id": inv["prize_id"]})
            if not prize: continue
            thumb = prize.get("thumb_url") or prize.get("image_url")
            if thumb:
                equipped_thumbs.append({"name": prize["name"], "thumb_url": thumb})
        rows.append({**r, "username": u.get("username"), "equipped_thumbs": equipped_thumbs,
                     "total_matches": r["wins"] + r["losses"]})
    rows.sort(key=lambda r: (r["wins"], r["net_credits"]), reverse=True)
    return {"game_id": game_id, "game_name": game.get("name"), "platform": game.get("platform"),
            "category": game.get("category"), "rows": rows}
