"""Highlight reels: upload, list, get, stream, delete."""
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import Depends, File, Form, HTTPException, Response, UploadFile

from core import (
    api_router, db, get_current_user,
    APP_NAME, HIGHLIGHT_ALLOWED_TYPES, HIGHLIGHT_MAX_BYTES, HIGHLIGHT_MAX_DURATION_SEC,
)
from services import put_object, get_object


@api_router.post("/highlights")
async def upload_highlight(
    file: UploadFile = File(...),
    title: str = Form(...),
    game_id: str = Form(""),
    duration_sec: float = Form(0.0),
    user: dict = Depends(get_current_user),
):
    """Upload a highlight reel video. Public by default. Max 60s / 50MB."""
    if file.content_type not in HIGHLIGHT_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only MP4, MOV, or WebM video files allowed")
    if not title or len(title.strip()) == 0:
        raise HTTPException(status_code=400, detail="Title required")
    if len(title) > 120:
        raise HTTPException(status_code=400, detail="Title too long (max 120 chars)")
    if duration_sec and duration_sec > HIGHLIGHT_MAX_DURATION_SEC:
        raise HTTPException(status_code=400, detail=f"Video too long (max {HIGHLIGHT_MAX_DURATION_SEC}s)")

    data = await file.read()
    if len(data) > HIGHLIGHT_MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    ext = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "mp4"
    path = f"{APP_NAME}/highlights/{user['id']}/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, file.content_type)

    game_name = ""
    if game_id:
        try:
            game = await db.games.find_one({"_id": ObjectId(game_id)})
            if game:
                game_name = game.get("name", "")
        except Exception:
            game_id = ""

    reel_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "title": title.strip(),
        "storage_path": result["path"],
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "duration_sec": float(duration_sec) if duration_sec else 0.0,
        "game_id": game_id,
        "game_name": game_name,
        "view_count": 0,
        "is_public": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.highlight_reels.insert_one(reel_doc)
    return {
        "id": reel_doc["id"],
        "title": reel_doc["title"],
        "game_name": game_name,
        "duration_sec": reel_doc["duration_sec"],
        "view_count": 0,
        "created_at": reel_doc["created_at"],
        "video_url": f"/api/highlights/{reel_doc['id']}/stream",
    }


@api_router.get("/highlights/user/{user_id}")
async def list_user_highlights(user_id: str):
    """Public list of a user's highlight reels (newest first)."""
    cursor = db.highlight_reels.find({"user_id": user_id, "is_public": True}).sort("created_at", -1).limit(100)
    items = await cursor.to_list(100)
    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "title": r["title"],
            "game_id": r.get("game_id", ""),
            "game_name": r.get("game_name", ""),
            "duration_sec": r.get("duration_sec", 0.0),
            "view_count": r.get("view_count", 0),
            "created_at": r["created_at"],
            "video_url": f"/api/highlights/{r['id']}/stream",
        }
        for r in items
    ]


@api_router.get("/highlights/{reel_id}")
async def get_highlight(reel_id: str):
    """Get highlight reel metadata (public). Increments view count."""
    reel = await db.highlight_reels.find_one({"id": reel_id, "is_public": True})
    if not reel:
        raise HTTPException(status_code=404, detail="Highlight not found")
    await db.highlight_reels.update_one({"id": reel_id}, {"$inc": {"view_count": 1}})
    owner = await db.users.find_one({"_id": ObjectId(reel["user_id"])})
    return {
        "id": reel["id"],
        "user_id": reel["user_id"],
        "username": owner["username"] if owner else "Unknown",
        "title": reel["title"],
        "game_id": reel.get("game_id", ""),
        "game_name": reel.get("game_name", ""),
        "duration_sec": reel.get("duration_sec", 0.0),
        "view_count": reel.get("view_count", 0) + 1,
        "created_at": reel["created_at"],
        "video_url": f"/api/highlights/{reel['id']}/stream",
    }


@api_router.get("/highlights/{reel_id}/stream")
async def stream_highlight(reel_id: str):
    """Stream the video bytes for a public highlight reel."""
    reel = await db.highlight_reels.find_one({"id": reel_id, "is_public": True})
    if not reel:
        raise HTTPException(status_code=404, detail="Highlight not found")
    data, content_type = get_object(reel["storage_path"])
    return Response(content=data, media_type=reel.get("content_type", content_type))


@api_router.delete("/highlights/{reel_id}")
async def delete_highlight(reel_id: str, user: dict = Depends(get_current_user)):
    """Delete a highlight reel (owner only)."""
    reel = await db.highlight_reels.find_one({"id": reel_id})
    if not reel:
        raise HTTPException(status_code=404, detail="Highlight not found")
    if reel["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can delete this highlight")
    await db.highlight_reels.delete_one({"id": reel_id})
    return {"ok": True}
