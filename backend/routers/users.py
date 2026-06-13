"""User profile, search, stats-by-game, countries, platforms, inventory, equip/unequip."""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException

from core import api_router, db, get_current_user
from models import ProfileUpdate, PublicProfileResponse, PrizeEquip
from services import build_public_profile


@api_router.put("/users/profile", response_model=PublicProfileResponse)
async def update_profile(profile_data: ProfileUpdate, user: dict = Depends(get_current_user)):
    """Update the current user's profile."""
    update_fields = {k: v for k, v in profile_data.model_dump(exclude_unset=True).items() if v is not None}

    if "country" in update_fields and update_fields["country"]:
        update_fields["country"] = update_fields["country"].upper()

    if update_fields.get("stake_min") is not None and update_fields.get("stake_max") is not None:
        if update_fields["stake_min"] > update_fields["stake_max"]:
            raise HTTPException(status_code=400, detail="stake_min cannot be greater than stake_max")

    valid_platforms = {"ps5", "ps4", "xbox_series", "xbox_one", "pc", "switch", "mobile"}
    if "platforms" in update_fields:
        invalid = set(update_fields["platforms"]) - valid_platforms
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid platforms: {invalid}")

    if "preferred_game_ids" in update_fields:
        for gid in update_fields["preferred_game_ids"]:
            try:
                exists = await db.games.find_one({"_id": ObjectId(gid)}, {"_id": 1})
                if not exists:
                    raise HTTPException(status_code=400, detail=f"Game {gid} does not exist")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=400, detail=f"Invalid game id: {gid}")

    if "whatsapp_phone" in update_fields:
        phone = (update_fields["whatsapp_phone"] or "").strip().replace(" ", "")
        if phone and not (phone.startswith("+") and phone[1:].isdigit() and 7 <= len(phone[1:]) <= 16):
            raise HTTPException(status_code=400, detail="WhatsApp number must be in E.164 format (e.g. +61412345678)")
        update_fields["whatsapp_phone"] = phone

    if update_fields:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update_fields})

    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    return await build_public_profile(user_doc)


@api_router.get("/users/me/profile", response_model=PublicProfileResponse)
async def get_my_profile(user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    return await build_public_profile(user_doc)


@api_router.get("/users/search")
async def search_users(
    q: Optional[str] = None,
    game_id: Optional[str] = None,
    country: Optional[str] = None,
    platform: Optional[str] = None,
    stake_min: Optional[float] = None,
    stake_max: Optional[float] = None,
    min_wins: Optional[int] = None,
    online_only: bool = False,
    limit: int = 50,
    current: dict = Depends(get_current_user)
):
    """Search players with filters. All filters AND together."""
    query: Dict[str, Any] = {"_id": {"$ne": ObjectId(current["id"])}}

    if q:
        import re
        q_safe = re.escape(q)
        query["$or"] = [
            {"username": {"$regex": q_safe, "$options": "i"}},
            {"bio": {"$regex": q_safe, "$options": "i"}},
        ]
    if game_id:
        query["preferred_game_ids"] = game_id
    if country:
        query["country"] = country.upper()
    if platform:
        query["platforms"] = platform
    if min_wins is not None:
        query["total_wins"] = {"$gte": min_wins}
    if stake_min is not None or stake_max is not None:
        s_min = stake_min if stake_min is not None else 0
        s_max = stake_max if stake_max is not None else 10**9
        query["$and"] = query.get("$and", []) + [
            {"stake_min": {"$lte": s_max}},
            {"stake_max": {"$gte": s_min}},
        ]
    if online_only:
        threshold = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        query["last_active_at"] = {"$gte": threshold}

    users = await db.users.find(query).sort([("last_active_at", -1), ("created_at", -1)]).limit(limit).to_list(limit)
    online_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    results = []
    for u in users:
        profile = await build_public_profile(u)
        profile["wallet_balance"] = 0.0
        profile["is_online"] = bool(profile.get("last_active_at") and profile["last_active_at"] >= online_cutoff)
        results.append(profile)
    return results


@api_router.get("/users/{user_id}/stats-by-game")
async def get_user_stats_by_game(user_id: str, current: dict = Depends(get_current_user)):
    """Aggregate per-game wins/losses + net credits won/lost for a user. Sourced from
    completed tournaments and confirmed head-to-head competition matches."""
    try:
        target = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    stats: Dict[str, Dict[str, Any]] = {}

    def _row(game_id: str, game_name: str, platform: str = ""):
        key = game_id
        if key not in stats:
            stats[key] = {
                "game_id": game_id,
                "game_name": game_name,
                "platform": platform,
                "wins": 0,
                "losses": 0,
                "credits_won": 0.0,
                "credits_lost": 0.0,
            }
        return stats[key]

    # --- Tournaments (completed) ---
    parts = await db.tournament_participants.find({"user_id": user_id}).to_list(2000)
    for p in parts:
        try:
            t = await db.tournaments.find_one({"_id": ObjectId(p["tournament_id"])})
        except Exception:
            continue
        if not t or t.get("status") not in ("completed",):
            continue
        if not t.get("winner_id"):
            continue
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])}) if t.get("game_id") else None
        game_id = t["game_id"]
        game_name = game.get("name") if game else "Unknown"
        platform = t.get("platform") or (game.get("platform") if game else "")
        row = _row(game_id, game_name, platform)
        stake = float(t.get("stake_amount", 0))
        n_players = int(t.get("max_players", 2))
        if t["winner_id"] == user_id:
            row["wins"] += 1
            row["credits_won"] += stake * (n_players - 1)
        else:
            row["losses"] += 1
            row["credits_lost"] += stake

    # --- Head-to-head competition matches (confirmed) ---
    comps = await db.competitions.find({
        "$or": [{"player_a_id": user_id}, {"player_b_id": user_id}]
    }).to_list(2000)
    for c in comps:
        game = await db.games.find_one({"_id": ObjectId(c["game_id"])}) if c.get("game_id") else None
        game_id = c["game_id"]
        game_name = game.get("name") if game else "Unknown"
        platform = c.get("platform") or (game.get("platform") if game else "")
        row = _row(game_id, game_name, platform)
        matches = await db.competition_matches.find({
            "competition_id": c["id"],
            "status": "confirmed",
        }).to_list(2000)
        for m in matches:
            stake = float(m.get("stake_amount", 0))
            if m.get("winner_user_id") == user_id:
                row["wins"] += 1
                row["credits_won"] += stake
            else:
                row["losses"] += 1
                row["credits_lost"] += stake

    rows = list(stats.values())
    for r in rows:
        r["net_credits"] = r["credits_won"] - r["credits_lost"]
        r["total_matches"] = r["wins"] + r["losses"]
    rows.sort(key=lambda r: (r["total_matches"], r["net_credits"]), reverse=True)

    summary = {
        "total_wins": sum(r["wins"] for r in rows),
        "total_losses": sum(r["losses"] for r in rows),
        "total_credits_won": sum(r["credits_won"] for r in rows),
        "total_credits_lost": sum(r["credits_lost"] for r in rows),
        "net_credits": sum(r["net_credits"] for r in rows),
    }
    return {"user_id": user_id, "summary": summary, "by_game": rows}


@api_router.get("/users/{user_id}", response_model=PublicProfileResponse)
async def get_user_profile(user_id: str, current: dict = Depends(get_current_user)):
    try:
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    profile = await build_public_profile(user_doc)
    if user_id != current["id"]:
        profile["wallet_balance"] = 0.0
    return profile


@api_router.get("/countries")
async def list_countries():
    """List of common gaming countries (ISO 2-letter codes + names)."""
    return [
        {"code": "AU", "name": "Australia"}, {"code": "US", "name": "United States"},
        {"code": "GB", "name": "United Kingdom"}, {"code": "CA", "name": "Canada"},
        {"code": "NZ", "name": "New Zealand"}, {"code": "DE", "name": "Germany"},
        {"code": "FR", "name": "France"}, {"code": "ES", "name": "Spain"},
        {"code": "IT", "name": "Italy"}, {"code": "JP", "name": "Japan"},
        {"code": "KR", "name": "South Korea"}, {"code": "BR", "name": "Brazil"},
        {"code": "MX", "name": "Mexico"}, {"code": "AR", "name": "Argentina"},
        {"code": "IN", "name": "India"}, {"code": "ZA", "name": "South Africa"},
        {"code": "NL", "name": "Netherlands"}, {"code": "SE", "name": "Sweden"},
        {"code": "NO", "name": "Norway"}, {"code": "DK", "name": "Denmark"},
        {"code": "FI", "name": "Finland"}, {"code": "IE", "name": "Ireland"},
        {"code": "PL", "name": "Poland"}, {"code": "RU", "name": "Russia"},
        {"code": "TR", "name": "Turkey"}, {"code": "AE", "name": "UAE"},
        {"code": "SG", "name": "Singapore"}, {"code": "PH", "name": "Philippines"},
        {"code": "ID", "name": "Indonesia"}, {"code": "MY", "name": "Malaysia"},
        {"code": "TH", "name": "Thailand"}, {"code": "VN", "name": "Vietnam"},
        {"code": "CN", "name": "China"}, {"code": "HK", "name": "Hong Kong"},
        {"code": "TW", "name": "Taiwan"}, {"code": "OTHER", "name": "Other"},
    ]


@api_router.get("/platforms-list")
async def platforms_list():
    return [
        {"code": "ps5", "name": "PlayStation 5"},
        {"code": "ps4", "name": "PlayStation 4"},
        {"code": "xbox_series", "name": "Xbox Series X/S"},
        {"code": "xbox_one", "name": "Xbox One"},
        {"code": "pc", "name": "PC"},
        {"code": "switch", "name": "Nintendo Switch"},
        {"code": "mobile", "name": "Mobile"},
    ]


@api_router.get("/users/{user_id}/inventory")
async def get_user_inventory(user_id: str, current: dict = Depends(get_current_user)):
    items = await db.user_prizes.find({"user_id": user_id}).to_list(500)
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    equipped = (user_doc or {}).get("equipped_prizes", {}) or {}
    out = []
    for inv in items:
        prize = await db.prizes.find_one({"id": inv["prize_id"]})
        if not prize:
            continue
        out.append({
            "inventory_id": inv["id"],
            "prize_id": prize["id"],
            "name": prize["name"],
            "kind": prize.get("kind", "image"),
            "image_url": prize.get("image_url") or "",
            "thumb_url": prize.get("thumb_url") or prize.get("image_url") or "",
            "asset": prize.get("asset", ""),
            "rarity": prize.get("rarity", "common"),
            "feat": prize.get("feat") or {},
            "redeemed_at": inv.get("redeemed_at"),
            "is_equipped": prize["id"] in equipped.values() if isinstance(equipped, dict) else False,
        })
    return {"user_id": user_id, "equipped": equipped, "items": out}


@api_router.post("/users/me/equip")
async def equip_prize(payload: PrizeEquip, user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    equipped = (user_doc or {}).get("equipped_prizes", {}) or {}
    if not payload.inventory_id:
        raise HTTPException(status_code=400, detail="inventory_id required")
    inv = await db.user_prizes.find_one({"id": payload.inventory_id, "user_id": user["id"]})
    if not inv:
        raise HTTPException(status_code=404, detail="You don't own this prize")
    prize = await db.prizes.find_one({"id": inv["prize_id"]})
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found")
    equipped[prize.get("kind", "image")] = payload.inventory_id
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"equipped_prizes": equipped}})
    return {"equipped": equipped}


@api_router.post("/users/me/unequip/{kind}")
async def unequip_prize(kind: str, user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    equipped = (user_doc or {}).get("equipped_prizes", {}) or {}
    equipped.pop(kind, None)
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"equipped_prizes": equipped}})
    return {"equipped": equipped}
