"""Admin-only latency analytics:
- Per-tournament / per-competition latency graph (time series per player)
- Continuous baseline samples (every 60s) from active match participants
- 30-day retention by default via TTL index — admin can extend retention on samples
  associated with an ongoing dispute.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException

from core import api_router, db, get_current_user, LATENCY_WARN_MS, LATENCY_HIGH_MS
from services import require_admin


def _classify(avg: float, peak: float) -> str:
    if peak >= LATENCY_HIGH_MS:
        return "high"
    if avg >= LATENCY_WARN_MS:
        return "warn"
    return "ok"


async def _attach_username(samples: list, user_field: str = "user_id") -> list:
    cache = {}
    out = []
    for s in samples:
        uid = s[user_field]
        if uid not in cache:
            u = await db.users.find_one({"_id": ObjectId(uid)})
            cache[uid] = u.get("username") if u else "Unknown"
        out.append({**s, "username": cache[uid]})
    return out


@api_router.get("/admin/latency/tournament/{tournament_id}")
async def admin_tournament_latency_graph(tournament_id: str, user: dict = Depends(get_current_user)):
    """Per-tournament latency graph data — admin only.
    Returns one time series per participant, ordered chronologically."""
    await require_admin(user)
    try:
        t = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Tournament not found")
    if not t:
        raise HTTPException(status_code=404, detail="Tournament not found")

    samples = await db.tournament_latency.find({"tournament_id": tournament_id}).sort("timestamp", 1).to_list(20000)

    series: dict = {}
    for s in samples:
        uid = s["user_id"]
        series.setdefault(uid, {"points": []})["points"].append({
            "t": s["timestamp"],
            "ms": float(s["latency_ms"]),
        })

    out = []
    for uid, data in series.items():
        u = await db.users.find_one({"_id": ObjectId(uid)})
        values = [p["ms"] for p in data["points"]]
        avg = sum(values) / len(values) if values else 0
        peak = max(values) if values else 0
        lo = min(values) if values else 0
        out.append({
            "user_id": uid,
            "username": u.get("username") if u else "Unknown",
            "points": data["points"],
            "sample_count": len(values),
            "avg_ms": round(avg, 1),
            "max_ms": round(peak, 1),
            "min_ms": round(lo, 1),
            "status": _classify(avg, peak),
        })
    return {
        "tournament_id": tournament_id,
        "status": t.get("status"),
        "stake_amount": t.get("stake_amount"),
        "started_at": t.get("started_at"),
        "disputed_at": t.get("disputed_at"),
        "completed_at": t.get("completed_at"),
        "thresholds": {"warn": LATENCY_WARN_MS, "high": LATENCY_HIGH_MS},
        "series": out,
    }


@api_router.get("/admin/latency/competition/{comp_id}")
async def admin_competition_latency_graph(comp_id: str, match_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Per-competition (or per-match) latency graph — admin only."""
    await require_admin(user)
    comp = await db.competitions.find_one({"id": comp_id})
    if not comp:
        raise HTTPException(status_code=404, detail="Competition not found")

    query = {"competition_id": comp_id}
    if match_id:
        query["match_id"] = match_id
    samples = await db.competition_latency.find(query).sort("timestamp", 1).to_list(20000)

    series: dict = {}
    for s in samples:
        uid = s["user_id"]
        series.setdefault(uid, {"points": []})["points"].append({
            "t": s["timestamp"],
            "ms": float(s["latency_ms"]),
            "match_id": s.get("match_id"),
        })

    out = []
    for uid, data in series.items():
        u = await db.users.find_one({"_id": ObjectId(uid)})
        values = [p["ms"] for p in data["points"]]
        avg = sum(values) / len(values) if values else 0
        peak = max(values) if values else 0
        lo = min(values) if values else 0
        out.append({
            "user_id": uid,
            "username": u.get("username") if u else "Unknown",
            "points": data["points"],
            "sample_count": len(values),
            "avg_ms": round(avg, 1),
            "max_ms": round(peak, 1),
            "min_ms": round(lo, 1),
            "status": _classify(avg, peak),
        })
    return {
        "competition_id": comp_id,
        "match_id": match_id,
        "status": comp.get("status"),
        "stake_per_match": comp.get("stake_per_match"),
        "thresholds": {"warn": LATENCY_WARN_MS, "high": LATENCY_HIGH_MS},
        "series": out,
    }


@api_router.get("/admin/latency/dashboard")
async def admin_latency_dashboard(q: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Searchable dashboard of every match with latency samples — disputed first, then active, then recent."""
    await require_admin(user)

    pipeline = [
        {"$group": {"_id": "$tournament_id", "count": {"$sum": 1},
                    "first_ts": {"$min": "$timestamp"}, "last_ts": {"$max": "$timestamp"}}}
    ]
    tlat = await db.tournament_latency.aggregate(pipeline).to_list(1000)

    items: List[dict] = []
    for row in tlat:
        try:
            t = await db.tournaments.find_one({"_id": ObjectId(row["_id"])})
        except Exception:
            continue
        if not t:
            continue
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])}) if t.get("game_id") else None
        if q:
            blob = f"{game.get('name','') if game else ''} {t.get('platform','')} {t.get('status','')}".lower()
            if q.lower() not in blob:
                continue
        items.append({
            "kind": "tournament",
            "id": row["_id"],
            "game_name": game.get("name") if game else "Unknown",
            "platform": t.get("platform"),
            "status": t.get("status"),
            "stake_amount": t.get("stake_amount"),
            "sample_count": row["count"],
            "first_ts": row["first_ts"],
            "last_ts": row["last_ts"],
            "is_disputed": t.get("status") == "disputed",
            "retention_extended": bool(t.get("latency_retention_extended_until")),
        })

    clat = await db.competition_latency.aggregate(pipeline_for_comp := [
        {"$group": {"_id": "$competition_id", "count": {"$sum": 1},
                    "first_ts": {"$min": "$timestamp"}, "last_ts": {"$max": "$timestamp"}}}
    ]).to_list(1000)
    for row in clat:
        c = await db.competitions.find_one({"id": row["_id"]})
        if not c:
            continue
        game = await db.games.find_one({"_id": ObjectId(c["game_id"])}) if c.get("game_id") else None
        if q:
            blob = f"{game.get('name','') if game else ''} {c.get('platform','')} {c.get('status','')}".lower()
            if q.lower() not in blob:
                continue
        cancelled = await db.competition_matches.count_documents({"competition_id": row["_id"], "status": "cancelled"})
        items.append({
            "kind": "competition",
            "id": row["_id"],
            "game_name": game.get("name") if game else "Unknown",
            "platform": c.get("platform"),
            "status": c.get("status"),
            "stake_amount": c.get("stake_per_match"),
            "sample_count": row["count"],
            "first_ts": row["first_ts"],
            "last_ts": row["last_ts"],
            "is_disputed": cancelled > 0,
            "retention_extended": bool(c.get("latency_retention_extended_until")),
        })

    items.sort(key=lambda i: (not i["is_disputed"], i.get("last_ts") or ""), reverse=False)
    items.reverse()
    items.sort(key=lambda i: (0 if i["is_disputed"] else 1, -(_ts(i.get("last_ts")))))
    return {"thresholds": {"warn": LATENCY_WARN_MS, "high": LATENCY_HIGH_MS}, "items": items}


def _ts(iso: Optional[str]) -> float:
    if not iso:
        return 0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


@api_router.post("/admin/latency/tournament/{tournament_id}/extend-retention")
async def extend_tournament_latency_retention(tournament_id: str, days: int = 90, user: dict = Depends(get_current_user)):
    """Extend the TTL for this tournament's latency samples by `days` days from now.
    Use this while a dispute is active so samples don't disappear in 30 days."""
    await require_admin(user)
    if days < 1 or days > 730:
        raise HTTPException(status_code=400, detail="days must be 1..730")
    new_expires = datetime.now(timezone.utc) + timedelta(days=days)
    res = await db.tournament_latency.update_many(
        {"tournament_id": tournament_id},
        {"$set": {"expires_at": new_expires}}
    )
    await db.tournaments.update_one(
        {"_id": ObjectId(tournament_id)},
        {"$set": {"latency_retention_extended_until": new_expires.isoformat()}}
    )
    return {"updated_samples": res.modified_count, "new_expiry": new_expires.isoformat()}


@api_router.post("/admin/latency/competition/{comp_id}/extend-retention")
async def extend_competition_latency_retention(comp_id: str, days: int = 90, user: dict = Depends(get_current_user)):
    await require_admin(user)
    if days < 1 or days > 730:
        raise HTTPException(status_code=400, detail="days must be 1..730")
    new_expires = datetime.now(timezone.utc) + timedelta(days=days)
    res = await db.competition_latency.update_many(
        {"competition_id": comp_id},
        {"$set": {"expires_at": new_expires}}
    )
    await db.competitions.update_one(
        {"id": comp_id},
        {"$set": {"latency_retention_extended_until": new_expires.isoformat()}}
    )
    return {"updated_samples": res.modified_count, "new_expiry": new_expires.isoformat()}
