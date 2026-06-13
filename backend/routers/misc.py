"""Misc endpoints: health/time + global leaderboard."""
import time as _t
from datetime import datetime, timezone

from bson import ObjectId

from core import api_router, db


@api_router.get("/health/time")
async def health_time():
    """Reports server timezone — useful to debug tournament time displays."""
    return {
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "server_time_local": datetime.now().isoformat(),
        "server_timezone": _t.tzname[0] if _t.tzname else "Unknown",
        "tz_offset_hours": -_t.timezone / 3600,
    }


@api_router.get("/leaderboard")
async def get_leaderboard():
    users = await db.users.find({}, {"_id": 1, "username": 1, "total_wins": 1, "total_losses": 1, "wallet_balance": 1, "equipped_prizes": 1}).sort("total_wins", -1).limit(50).to_list(50)
    result = []
    for u in users:
        equipped_thumbs = []
        equipped = (u.get("equipped_prizes") or {}) if isinstance(u.get("equipped_prizes"), dict) else {}
        for inv_id in set(equipped.values()):
            inv = await db.user_prizes.find_one({"id": inv_id, "user_id": str(u["_id"])})
            if not inv:
                continue
            prize = await db.prizes.find_one({"id": inv["prize_id"]})
            if not prize:
                continue
            thumb = prize.get("thumb_url") or prize.get("image_url")
            if thumb:
                equipped_thumbs.append({"name": prize["name"], "thumb_url": thumb})
        result.append({
            "user_id": str(u["_id"]),
            "username": u["username"],
            "wins": u.get("total_wins", 0),
            "losses": u.get("total_losses", 0),
            "balance": u.get("wallet_balance", 0.0),
            "equipped_thumbs": equipped_thumbs,
        })
    return result
