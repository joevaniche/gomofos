"""Prizes: catalog, redeem, admin create/update/delete, prize-image upload, seed, public storage server."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import Depends, File, HTTPException, Response, UploadFile

from core import api_router, db, get_current_user
from models import PrizeCreate
from services import (
    SEED_PRIZES, check_feat_unlocked, prize_dict,
    put_object, get_object, require_admin,
)


@api_router.post("/admin/prizes/seed")
async def seed_prizes(user: dict = Depends(get_current_user)):
    await require_admin(user)
    created = 0
    for p in SEED_PRIZES:
        existing = await db.prizes.find_one({"name": p["name"]})
        if existing:
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "kind": "image",
            "image_url": "",
            "thumb_url": "",
            "asset": "",
            "rarity": "common",
            "description": "",
            "active": True,
            **p,
        }
        await db.prizes.insert_one(doc)
        created += 1
    return {"created": created, "total": await db.prizes.count_documents({})}


@api_router.get("/prizes")
async def list_prizes(kind: Optional[str] = None, current: dict = Depends(get_current_user)):
    """Catalog of redeemable prizes with per-user unlock state."""
    query: Dict[str, Any] = {"active": True}
    if kind:
        query["kind"] = kind
    cursor = db.prizes.find(query).sort([("cost", 1)])
    items = await cursor.to_list(500)
    return [await prize_dict(p, with_unlock_for=current["id"]) for p in items]


@api_router.post("/admin/prizes")
async def admin_create_prize(payload: PrizeCreate, user: dict = Depends(get_current_user)):
    await require_admin(user)
    if payload.cost <= 0:
        raise HTTPException(status_code=400, detail="cost must be > 0")
    feat_doc = payload.feat.model_dump() if payload.feat else None
    if feat_doc and feat_doc.get("type") not in (None, "", "tournament_wins", "h2h_wins", "wins_in_genre", "streak", "streak_in_genre", "net_credits"):
        raise HTTPException(status_code=400, detail="Unknown feat type")
    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name.strip()[:80],
        "description": (payload.description or "").strip()[:300],
        "kind": "image",
        "cost": float(payload.cost),
        "asset": (payload.asset or "").strip()[:80],
        "image_url": (payload.image_url or "").strip()[:500],
        "thumb_url": (payload.thumb_url or "").strip()[:500],
        "rarity": (payload.rarity or "common").strip()[:20],
        "feat": feat_doc,
        "active": True if payload.active is None else bool(payload.active),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.prizes.insert_one(doc)
    return await prize_dict(doc, with_unlock_for=user["id"])


@api_router.patch("/admin/prizes/{prize_id}")
async def admin_update_prize(prize_id: str, payload: PrizeCreate, user: dict = Depends(get_current_user)):
    await require_admin(user)
    feat_doc = payload.feat.model_dump() if payload.feat else None
    update = {
        "name": payload.name.strip()[:80],
        "description": (payload.description or "").strip()[:300],
        "kind": "image",
        "cost": float(payload.cost),
        "asset": (payload.asset or "").strip()[:80],
        "image_url": (payload.image_url or "").strip()[:500],
        "thumb_url": (payload.thumb_url or "").strip()[:500],
        "rarity": (payload.rarity or "common").strip()[:20],
        "feat": feat_doc,
        "active": bool(payload.active),
    }
    res = await db.prizes.update_one({"id": prize_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Prize not found")
    doc = await db.prizes.find_one({"id": prize_id})
    return await prize_dict(doc, with_unlock_for=user["id"])


@api_router.delete("/admin/prizes/{prize_id}")
async def admin_delete_prize(prize_id: str, user: dict = Depends(get_current_user)):
    await require_admin(user)
    res = await db.prizes.update_one({"id": prize_id}, {"$set": {"active": False}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Prize not found")
    return {"status": "disabled"}


@api_router.post("/admin/prize-image")
async def admin_upload_prize_image(
    file: UploadFile = File(...),
    kind: str = "main",        # "main" or "thumb"
    user: dict = Depends(get_current_user)
):
    """Uploads a prize image, returns the public URL the admin should paste into image_url/thumb_url."""
    await require_admin(user)
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 8 MB)")
    ext = (file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "png").lower()
    if ext not in ("png", "jpg", "jpeg", "webp", "gif"):
        raise HTTPException(status_code=400, detail="Only png/jpg/jpeg/webp/gif allowed")
    obj_path = f"prize-images/{kind}-{uuid.uuid4().hex}.{ext}"
    put_object(obj_path, data, file.content_type or f"image/{ext}")
    return {"url": f"/api/storage/{obj_path}"}


@api_router.get("/storage/{path:path}")
async def serve_storage(path: str):
    """Public file server for uploaded prize/profile images. No auth so <img src> works everywhere."""
    data, ct = get_object(path)
    return Response(content=data, media_type=ct)


@api_router.post("/prizes/{prize_id}/redeem")
async def redeem_prize(prize_id: str, user: dict = Depends(get_current_user)):
    prize = await db.prizes.find_one({"id": prize_id, "active": True})
    if not prize:
        raise HTTPException(status_code=404, detail="Prize not found or no longer available")
    unlock = await check_feat_unlocked(user["id"], prize.get("feat") or {})
    if not unlock["met"]:
        raise HTTPException(status_code=403,
            detail=f"Locked — earn {int(unlock['target'])} (you have {int(unlock['progress'])}) to unlock this prize.")
    already_owned = await db.user_prizes.find_one({"user_id": user["id"], "prize_id": prize_id})
    if already_owned:
        raise HTTPException(status_code=400, detail="You already own this prize")
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    bal = float(user_doc.get("wallet_balance", 0.0) or 0.0)
    if bal < float(prize["cost"]):
        raise HTTPException(status_code=400, detail=f"Insufficient credits (need {prize['cost']} CR, have {bal:.0f} CR)")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -float(prize["cost"])}})
    inv_id = str(uuid.uuid4())
    await db.user_prizes.insert_one({
        "id": inv_id,
        "user_id": user["id"],
        "prize_id": prize_id,
        "redeemed_at": now_iso,
    })
    await db.wallet_transactions.insert_one({
        "user_id": user["id"], "amount": -float(prize["cost"]), "type": "debit",
        "reference_type": "prize_redeem", "reference_id": prize_id, "timestamp": now_iso,
    })
    return {"inventory_id": inv_id, "remaining_balance": bal - float(prize["cost"])}
