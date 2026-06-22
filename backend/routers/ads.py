"""Advertising platform:
- Admin or ad-manager can CRUD ads
- Admin can promote other users to ad-managers via `can_manage_ads` flag
- Logged-in users fetch active ads rotation
- Click + impression tracking
- Image upload via existing storage backend
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from core import api_router, db, get_current_user
from services import put_object


# ============ MODELS ============
class AdCreate(BaseModel):
    name: str
    image_url: str
    click_url: str
    active: Optional[bool] = True


class AdManagerGrant(BaseModel):
    user_id: str


async def _require_ad_admin(user: dict) -> dict:
    """Allow if site admin OR user has can_manage_ads flag."""
    udoc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not udoc:
        raise HTTPException(status_code=403, detail="Forbidden")
    if udoc.get("role") == "admin" or udoc.get("can_manage_ads") is True:
        return udoc
    raise HTTPException(status_code=403, detail="Only admins or ad managers can do this")


def _ad_dict(ad: dict) -> dict:
    return {
        "id": ad["id"],
        "name": ad["name"],
        "image_url": ad["image_url"],
        "click_url": ad["click_url"],
        "active": bool(ad.get("active", True)),
        "click_count": int(ad.get("click_count", 0)),
        "impression_count": int(ad.get("impression_count", 0)),
        "created_by": ad.get("created_by"),
        "created_by_username": ad.get("created_by_username"),
        "created_at": ad.get("created_at"),
    }


# ============ AD ROTATION (logged-in users) ============
@api_router.get("/ads/rotation")
async def get_ad_rotation(limit: int = 12, user: dict = Depends(get_current_user)):
    """Return up to `limit` active ads for the rotating right-rail. Client picks 3
    to display + rotates client-side every 5s. Records nothing here — impressions
    are reported by the client (so reload spamming doesn't inflate)."""
    cursor = db.advertisements.find({"active": True}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(limit)
    return [_ad_dict(a) for a in items]


@api_router.post("/ads/{ad_id}/impression")
async def record_ad_impression(ad_id: str, user: dict = Depends(get_current_user)):
    """Client tells us when an ad was actually shown."""
    await db.advertisements.update_one({"id": ad_id, "active": True}, {"$inc": {"impression_count": 1}})
    return {"ok": True}


@api_router.get("/ads/{ad_id}/click")
async def record_ad_click(ad_id: str):
    """Public click tracking — bumps counter and 302 redirects to click_url. No auth
    so the analytics survive if the user is logging out / on landing page."""
    ad = await db.advertisements.find_one({"id": ad_id})
    if not ad or not ad.get("active", True):
        raise HTTPException(status_code=404, detail="Ad not found")
    await db.advertisements.update_one({"id": ad_id}, {"$inc": {"click_count": 1}})
    return RedirectResponse(url=ad["click_url"], status_code=302)


# ============ ADMIN CRUD ============
@api_router.get("/admin/ads")
async def list_ads_for_admin(q: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Searchable list of every ad. Search matches name (case-insensitive) and click_url."""
    await _require_ad_admin(user)
    query = {}
    if q:
        import re
        q_safe = re.escape(q.strip())
        query["$or"] = [
            {"name": {"$regex": q_safe, "$options": "i"}},
            {"click_url": {"$regex": q_safe, "$options": "i"}},
        ]
    items = await db.advertisements.find(query).sort("created_at", -1).to_list(500)
    return [_ad_dict(a) for a in items]


@api_router.post("/admin/ads")
async def create_ad(payload: AdCreate, user: dict = Depends(get_current_user)):
    udoc = await _require_ad_admin(user)
    name = (payload.name or "").strip()
    image_url = (payload.image_url or "").strip()
    click_url = (payload.click_url or "").strip()
    if not name or not image_url or not click_url:
        raise HTTPException(status_code=400, detail="name, image_url and click_url are all required")
    if not click_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="click_url must start with http:// or https://")
    doc = {
        "id": str(uuid.uuid4()),
        "name": name[:120],
        "image_url": image_url[:500],
        "click_url": click_url[:500],
        "active": bool(payload.active),
        "click_count": 0,
        "impression_count": 0,
        "created_by": user["id"],
        "created_by_username": udoc.get("username"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.advertisements.insert_one(doc)
    return _ad_dict(doc)


@api_router.patch("/admin/ads/{ad_id}")
async def update_ad(ad_id: str, payload: AdCreate, user: dict = Depends(get_current_user)):
    await _require_ad_admin(user)
    upd = {
        "name": (payload.name or "").strip()[:120],
        "image_url": (payload.image_url or "").strip()[:500],
        "click_url": (payload.click_url or "").strip()[:500],
        "active": bool(payload.active),
    }
    res = await db.advertisements.update_one({"id": ad_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ad not found")
    ad = await db.advertisements.find_one({"id": ad_id})
    return _ad_dict(ad)


@api_router.delete("/admin/ads/{ad_id}")
async def delete_ad(ad_id: str, user: dict = Depends(get_current_user)):
    await _require_ad_admin(user)
    res = await db.advertisements.delete_one({"id": ad_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ad not found")
    return {"deleted": ad_id}


@api_router.post("/admin/ads/upload-image")
async def upload_ad_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Uploads ad creative — returns public URL for the admin to paste into the form."""
    await _require_ad_admin(user)
    data = await file.read()
    if len(data) > 4 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 4 MB)")
    if file.content_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        raise HTTPException(status_code=400, detail="Only PNG / JPEG / WEBP / GIF")
    ext = (file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "png").lower()
    path = f"ads/{uuid.uuid4().hex}.{ext}"
    put_object(path, data, file.content_type)
    return {"url": f"/api/storage/{path}"}


# ============ AD-MANAGER ROLE MANAGEMENT (admin-only) ============
async def _require_site_admin(user: dict) -> dict:
    udoc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not udoc or udoc.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Site admin only")
    return udoc


@api_router.get("/admin/ad-managers")
async def list_ad_managers(user: dict = Depends(get_current_user)):
    """List every user who is either role=admin or can_manage_ads=True."""
    await _require_site_admin(user)
    items = await db.users.find({
        "$or": [{"role": "admin"}, {"can_manage_ads": True}]
    }, {"_id": 1, "email": 1, "username": 1, "role": 1, "can_manage_ads": 1}).to_list(500)
    return [{
        "id": str(u["_id"]),
        "email": u.get("email"),
        "username": u.get("username"),
        "role": u.get("role"),
        "can_manage_ads": bool(u.get("can_manage_ads")),
        "is_site_admin": u.get("role") == "admin",
    } for u in items]


@api_router.post("/admin/ad-managers")
async def grant_ad_manager(payload: AdManagerGrant, user: dict = Depends(get_current_user)):
    await _require_site_admin(user)
    try:
        target = await db.users.find_one({"_id": ObjectId(payload.user_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"_id": ObjectId(payload.user_id)}, {"$set": {"can_manage_ads": True}})
    return {"granted": payload.user_id, "username": target.get("username")}


@api_router.delete("/admin/ad-managers/{user_id}")
async def revoke_ad_manager(user_id: str, user: dict = Depends(get_current_user)):
    await _require_site_admin(user)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"can_manage_ads": False}})
    return {"revoked": user_id}
