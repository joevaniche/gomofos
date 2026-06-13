"""Chat: send messages + retrieve."""
from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from fastapi import Depends, HTTPException

from core import api_router, db, get_current_user
from models import ChatMessageCreate, ChatMessageResponse


@api_router.post("/chat", response_model=ChatMessageResponse)
async def send_message(msg_data: ChatMessageCreate, user: dict = Depends(get_current_user)):
    participant = await db.tournament_participants.find_one({"tournament_id": msg_data.tournament_id, "user_id": user["id"]})
    if not participant:
        raise HTTPException(status_code=403, detail="Only tournament participants can chat")

    msg_doc = {
        "tournament_id": msg_data.tournament_id,
        "user_id": user["id"],
        "message": msg_data.message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = await db.chat_messages.insert_one(msg_doc)
    return ChatMessageResponse(
        id=str(result.inserted_id),
        tournament_id=msg_data.tournament_id,
        user_id=user["id"],
        username=user["username"],
        message=msg_data.message,
        timestamp=msg_doc["timestamp"]
    )


@api_router.get("/chat/{tournament_id}", response_model=List[ChatMessageResponse])
async def get_messages(tournament_id: str):
    messages = await db.chat_messages.find({"tournament_id": tournament_id}).sort("timestamp", 1).to_list(1000)
    result = []
    for m in messages:
        u = await db.users.find_one({"_id": ObjectId(m["user_id"])})
        result.append(ChatMessageResponse(
            id=str(m["_id"]),
            tournament_id=m["tournament_id"],
            user_id=m["user_id"],
            username=u["username"] if u else "Unknown",
            message=m["message"],
            timestamp=m["timestamp"]
        ))
    return result
