"""Shared application singletons, JWT helpers, dependencies, and module-level constants.

Every router imports `api_router`/`app` from here and registers its routes via decorators
at module-load time. `server.py` then includes the api_router on the app.
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
import asyncio
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Request

from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# FastAPI app + main api router
app = FastAPI()
api_router = APIRouter(prefix="/api")

# JWT
JWT_ALGORITHM = "HS256"


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_decline_token(tournament_id: str, invitee_user_id: str) -> str:
    """Signed one-click token (valid 7 days) authorising the invitee to decline a private challenge."""
    payload = {
        "tid": tournament_id,
        "uid": invitee_user_id,
        "type": "decline_challenge",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Update last_active_at (fire and forget — don't block request)
        try:
            asyncio.create_task(db.users.update_one(
                {"_id": ObjectId(payload["sub"])},
                {"$set": {"last_active_at": datetime.now(timezone.utc).isoformat()}}
            ))
        except Exception:
            pass
        user["id"] = str(user["_id"])
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ============ Module-level constants ============
WELCOME_BONUS = 1000.0
REFERRAL_BONUS = 500.0

# Latency policy thresholds (single source of truth for backend + dispute logic)
LATENCY_WARN_MS = 100
LATENCY_HIGH_MS = 200

# Dispute auto-hold thresholds
DISPUTE_HOLD_THRESHOLD = 0.66        # 66 %
DISPUTE_HOLD_MIN_MATCHES = 3         # need at least 3 decided matches before suspending

# Storage
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "gomofos"
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local").lower()  # "local" or "emergent"
STORAGE_LOCAL_PATH = os.environ.get("STORAGE_LOCAL_PATH", "/var/www/gomofos/uploads")

# Highlight reel limits
HIGHLIGHT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
HIGHLIGHT_MAX_DURATION_SEC = 60
HIGHLIGHT_ALLOWED_TYPES = {"video/mp4", "video/quicktime", "video/webm"}

# Admin 2FA
TWOFA_CODE_TTL_SECONDS = 300        # 5 min
TWOFA_MAX_ATTEMPTS = 3
