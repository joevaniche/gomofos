from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File, Form, WebSocket, WebSocketDisconnect, Header, Query
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import os
import logging
import bcrypt
import jwt
import secrets
import uuid
import requests
import asyncio
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

from email_service import send_match_invite, send_dispute_alert

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Auth helpers
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

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    wallet_balance: float
    total_wins: int
    total_losses: int
    rank: int
    role: Optional[str] = None
    created_at: str

class GameCreate(BaseModel):
    name: str
    platform: str
    image_url: Optional[str] = None
    category: Optional[str] = None

class GameResponse(BaseModel):
    id: str
    name: str
    platform: str
    image_url: Optional[str]
    category: Optional[str] = None
    created_at: str

class TournamentCreate(BaseModel):
    game_id: str
    stake_amount: float
    max_players: int
    start_time: str

class TournamentResponse(BaseModel):
    id: str
    game_id: str
    game_name: str
    creator_id: str
    creator_username: str
    stake_amount: float
    status: str
    max_players: int
    current_players: int
    winner_id: Optional[str]
    start_time: str
    created_at: str

class ChatMessageCreate(BaseModel):
    tournament_id: str
    message: str

class ChatMessageResponse(BaseModel):
    id: str
    tournament_id: str
    user_id: str
    username: str
    message: str
    timestamp: str

class DepositRequest(BaseModel):
    amount: float
    origin_url: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# === PROFILE MODELS ===
class ProfileUpdate(BaseModel):
    bio: Optional[str] = None
    country: Optional[str] = None       # ISO 2-letter code, e.g., "AU"
    city: Optional[str] = None
    timezone: Optional[str] = None      # IANA name, e.g., "Australia/Sydney"
    platforms: Optional[List[str]] = None  # ["ps5","xbox_series","pc",...]
    gamertags: Optional[Dict[str, str]] = None  # {"psn":"...","xbox":"...","steam":"..."}
    preferred_game_ids: Optional[List[str]] = None
    stake_min: Optional[float] = None
    stake_max: Optional[float] = None

class PublicProfileResponse(BaseModel):
    id: str
    username: str
    bio: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    timezone: Optional[str] = None
    platforms: List[str] = []
    gamertags: Dict[str, str] = {}
    preferred_game_ids: List[str] = []
    preferred_games: List[Dict[str, str]] = []  # populated [{id,name,platform}]
    stake_min: Optional[float] = None
    stake_max: Optional[float] = None
    total_wins: int
    total_losses: int
    wallet_balance: float
    last_active_at: Optional[str] = None
    created_at: str

# === CHALLENGE / PRIVATE TOURNAMENT ===
class ChallengeCreate(BaseModel):
    opponent_user_id: str
    game_id: str
    stake_amount: float
    start_time: str


# Auth endpoints
@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserRegister, response: Response):
    email = user_data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = hash_password(user_data.password)
    # Play-money mode: new users get 1000 free credits to start
    WELCOME_BONUS = 1000.0
    user_doc = {
        "email": email,
        "username": user_data.username,
        "password_hash": hashed_pw,
        "wallet_balance": WELCOME_BONUS,
        "total_wins": 0,
        "total_losses": 0,
        "rank": 0,
        "last_daily_bonus": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    # Log the welcome bonus as a wallet transaction
    await db.wallet_transactions.insert_one({
        "user_id": user_id,
        "amount": WELCOME_BONUS,
        "type": "credit",
        "reference_type": "welcome_bonus",
        "reference_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return UserResponse(
        id=user_id,
        email=email,
        username=user_data.username,
        wallet_balance=WELCOME_BONUS,
        total_wins=0,
        total_losses=0,
        rank=0,
        role=None,
        created_at=user_doc["created_at"]
    )

@api_router.post("/auth/login", response_model=UserResponse)
async def login(credentials: UserLogin, request: Request, response: Response):
    email = credentials.email.lower()
    ip = request.client.host
    identifier = f"{ip}:{email}"
    
    # Check brute force
    attempt_doc = await db.login_attempts.find_one({"identifier": identifier})
    if attempt_doc and attempt_doc.get("count", 0) >= 5:
        lockout_until = attempt_doc.get("locked_until")
        if lockout_until and datetime.now(timezone.utc) < lockout_until:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        # Increment failed attempts
        if attempt_doc:
            new_count = attempt_doc.get("count", 0) + 1
            update_data = {"count": new_count}
            if new_count >= 5:
                update_data["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=15)
            await db.login_attempts.update_one({"identifier": identifier}, {"$set": update_data})
        else:
            await db.login_attempts.insert_one({"identifier": identifier, "count": 1})
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Clear failed attempts
    await db.login_attempts.delete_one({"identifier": identifier})
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return UserResponse(
        id=user_id,
        email=user["email"],
        username=user["username"],
        wallet_balance=user.get("wallet_balance", 0.0),
        total_wins=user.get("total_wins", 0),
        total_losses=user.get("total_losses", 0),
        rank=user.get("rank", 0),
        role=user.get("role"),
        created_at=user["created_at"]
    )

@api_router.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    return UserResponse(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        wallet_balance=user.get("wallet_balance", 0.0),
        total_wins=user.get("total_wins", 0),
        total_losses=user.get("total_losses", 0),
        rank=user.get("rank", 0),
        role=user.get("role"),
        created_at=user["created_at"]
    )

@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_id = str(user["_id"])
        new_access_token = create_access_token(user_id, user["email"])
        response.set_cookie(key="access_token", value=new_access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@api_router.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    email = req.email.lower()
    user = await db.users.find_one({"email": email})
    if not user:
        return {"message": "If email exists, reset link has been sent"}
    
    token = secrets.token_urlsafe(32)
    await db.password_reset_tokens.insert_one({
        "token": token,
        "user_id": str(user["_id"]),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "used": False
    })
    
    reset_link = f"{os.environ.get('FRONTEND_URL')}/reset-password?token={token}"
    print(f"Password reset link: {reset_link}")
    return {"message": "If email exists, reset link has been sent"}

@api_router.post("/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    token_doc = await db.password_reset_tokens.find_one({"token": req.token})
    if not token_doc or token_doc.get("used") or datetime.now(timezone.utc) > token_doc["expires_at"]:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    hashed_pw = hash_password(req.new_password)
    await db.users.update_one({"_id": ObjectId(token_doc["user_id"])}, {"$set": {"password_hash": hashed_pw}})
    await db.password_reset_tokens.update_one({"token": req.token}, {"$set": {"used": True}})
    
    return {"message": "Password reset successfully"}

# === PROFILE & PLAYER SEARCH ===
async def _build_public_profile(user_doc) -> dict:
    """Convert user doc to public profile dict, populating preferred_games."""
    preferred_ids = user_doc.get("preferred_game_ids") or []
    preferred_games = []
    for gid in preferred_ids:
        try:
            g = await db.games.find_one({"_id": ObjectId(gid)})
            if g:
                preferred_games.append({"id": str(g["_id"]), "name": g["name"], "platform": g["platform"]})
        except Exception:
            continue
    return {
        "id": str(user_doc["_id"]),
        "username": user_doc["username"],
        "bio": user_doc.get("bio"),
        "country": user_doc.get("country"),
        "city": user_doc.get("city"),
        "timezone": user_doc.get("timezone"),
        "platforms": user_doc.get("platforms") or [],
        "gamertags": user_doc.get("gamertags") or {},
        "preferred_game_ids": preferred_ids,
        "preferred_games": preferred_games,
        "stake_min": user_doc.get("stake_min"),
        "stake_max": user_doc.get("stake_max"),
        "total_wins": user_doc.get("total_wins", 0),
        "total_losses": user_doc.get("total_losses", 0),
        "wallet_balance": user_doc.get("wallet_balance", 0.0),
        "last_active_at": user_doc.get("last_active_at"),
        "created_at": user_doc["created_at"],
    }

@api_router.put("/users/profile", response_model=PublicProfileResponse)
async def update_profile(profile_data: ProfileUpdate, user: dict = Depends(get_current_user)):
    """Update the current user's profile."""
    update_fields = {k: v for k, v in profile_data.model_dump(exclude_unset=True).items() if v is not None}
    
    # Normalize country to uppercase
    if "country" in update_fields and update_fields["country"]:
        update_fields["country"] = update_fields["country"].upper()
    
    # Validate stake range
    if update_fields.get("stake_min") is not None and update_fields.get("stake_max") is not None:
        if update_fields["stake_min"] > update_fields["stake_max"]:
            raise HTTPException(status_code=400, detail="stake_min cannot be greater than stake_max")
    
    # Validate platforms
    valid_platforms = {"ps5", "ps4", "xbox_series", "xbox_one", "pc", "switch", "mobile"}
    if "platforms" in update_fields:
        invalid = set(update_fields["platforms"]) - valid_platforms
        if invalid:
            raise HTTPException(status_code=400, detail=f"Invalid platforms: {invalid}")
    
    # Validate preferred games
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
    
    if update_fields:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update_fields})
    
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    return await _build_public_profile(user_doc)

@api_router.get("/users/me/profile", response_model=PublicProfileResponse)
async def get_my_profile(user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    return await _build_public_profile(user_doc)

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
    query: Dict[str, Any] = {"_id": {"$ne": ObjectId(current["id"])}}  # exclude self
    
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
        # Only match users who have set a stake range that overlaps
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
        profile = await _build_public_profile(u)
        # Hide wallet_balance from other users
        profile["wallet_balance"] = 0.0
        profile["is_online"] = bool(profile.get("last_active_at") and profile["last_active_at"] >= online_cutoff)
        results.append(profile)
    return results

@api_router.get("/users/{user_id}", response_model=PublicProfileResponse)
async def get_user_profile(user_id: str, current: dict = Depends(get_current_user)):
    try:
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    profile = await _build_public_profile(user_doc)
    # Hide wallet_balance if viewing someone else's profile
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

@api_router.post("/challenges")
async def create_challenge(challenge: ChallengeCreate, user: dict = Depends(get_current_user)):
    """Create a private 1v1 tournament invite for a specific opponent."""
    if challenge.opponent_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot challenge yourself")
    if challenge.stake_amount <= 0:
        raise HTTPException(status_code=400, detail="Stake amount must be greater than 0")
    
    opponent = await db.users.find_one({"_id": ObjectId(challenge.opponent_user_id)})
    if not opponent:
        raise HTTPException(status_code=404, detail="Opponent not found")
    
    game = await db.games.find_one({"_id": ObjectId(challenge.game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    user_data = await db.users.find_one({"_id": ObjectId(user["id"])})
    if user_data.get("wallet_balance", 0.0) < challenge.stake_amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -challenge.stake_amount}})
    
    tournament_doc = {
        "game_id": challenge.game_id,
        "creator_id": user["id"],
        "stake_amount": challenge.stake_amount,
        "status": "open",
        "max_players": 2,
        "current_players": 1,
        "winner_id": None,
        "start_time": challenge.start_time,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_private": True,
        "invited_user_ids": [challenge.opponent_user_id],
    }
    result = await db.tournaments.insert_one(tournament_doc)
    
    await db.tournament_participants.insert_one({
        "tournament_id": str(result.inserted_id),
        "user_id": user["id"],
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "result_status": "pending"
    })

    # Fire-and-forget challenge email to the opponent (skipped if SendGrid not configured)
    if opponent.get("email"):
        decline_token = create_decline_token(str(result.inserted_id), str(opponent["_id"]))
        asyncio.create_task(send_match_invite(
            to_email=opponent["email"],
            opponent_username=opponent.get("username", "Mofo"),
            challenger_username=user_data.get("username", "A challenger"),
            game_name=game.get("name", "the game"),
            stake_amount=float(challenge.stake_amount),
            tournament_id=str(result.inserted_id),
            app_url=os.environ.get("FRONTEND_URL", "https://gomofos.com"),
            decline_token=decline_token,
        ))

    return {
        "tournament_id": str(result.inserted_id),
        "opponent_username": opponent["username"],
        "stake_amount": challenge.stake_amount,
        "message": f"Challenge sent to {opponent['username']}"
    }


async def _decline_challenge_core(token: str) -> dict:
    """Validate the decline token, mark the challenge declined, refund both stakes.

    Returns {status, title, message, tournament_id}. The status field is one of:
    'ok' (just declined), 'already' (was already declined/cancelled), 'started'
    (cannot decline once the match started), 'invalid' (bad token), 'expired'.
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {"status": "expired", "title": "Link expired", "message": "This decline link is no longer valid.", "tournament_id": None}
    except jwt.InvalidTokenError:
        return {"status": "invalid", "title": "Invalid link", "message": "This decline link is malformed.", "tournament_id": None}

    if payload.get("type") != "decline_challenge":
        return {"status": "invalid", "title": "Invalid link", "message": "This link is not authorised to decline a challenge.", "tournament_id": None}

    tournament_id = payload.get("tid")
    invitee_id = payload.get("uid")

    try:
        tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    except Exception:
        tournament = None
    if not tournament:
        return {"status": "invalid", "title": "Challenge not found", "message": "We couldn't find that challenge — it may have been deleted.", "tournament_id": tournament_id}

    if str(invitee_id) not in (tournament.get("invited_user_ids") or []):
        return {"status": "invalid", "title": "Not your challenge", "message": "This decline link doesn't match the invited player.", "tournament_id": tournament_id}

    status = tournament.get("status")
    if status == "declined":
        return {"status": "already", "title": "Already declined", "message": "This challenge was already declined and stakes were refunded.", "tournament_id": tournament_id}
    if status != "open":
        return {"status": "started", "title": "Match already started", "message": f"This match is {status.replace('_', ' ')} — you can no longer decline it. Open the tournament page to continue.", "tournament_id": tournament_id}

    # Refund every participant who already paid in
    participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(100)
    stake = float(tournament.get("stake_amount", 0.0))
    refunded = []
    for p in participants:
        try:
            await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"wallet_balance": stake}})
            refunded.append(p["user_id"])
        except Exception as e:  # noqa: BLE001
            logger.error("Refund failed for user %s on tournament %s: %s", p.get("user_id"), tournament_id, e)

    await db.tournaments.update_one(
        {"_id": ObjectId(tournament_id)},
        {"$set": {
            "status": "declined",
            "declined_by": invitee_id,
            "declined_at": datetime.now(timezone.utc).isoformat(),
            "refunded_user_ids": refunded,
        }}
    )

    if len(refunded) == 1:
        msg = f"Got it — challenge declined and {stake:.0f} CR was refunded to the challenger."
    else:
        msg = f"Got it — challenge declined and {len(refunded) * stake:.0f} CR was refunded to {len(refunded)} players."

    return {
        "status": "ok",
        "title": "Challenge declined",
        "message": msg,
        "tournament_id": tournament_id,
    }


@app.get("/api/challenges/decline", response_class=HTMLResponse)
async def decline_challenge_via_link(token: str):
    """One-click decline endpoint linked from match-invite emails.

    Unauthenticated by design — the signed token in the URL is the authorisation.
    Returns a small HTML confirmation page so it works directly from the email client.
    """
    result = await _decline_challenge_core(token)
    base = (os.environ.get("FRONTEND_URL", "https://gomofos.com")).rstrip("/")
    cta_url = f"{base}/tournament/{result['tournament_id']}" if result.get("tournament_id") else base
    color = "#22C55E" if result["status"] == "ok" else ("#F59E0B" if result["status"] in ("already",) else "#EF4444")
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{result['title']} · Gomofos</title>
<style>
body{{margin:0;background:#0A0A0A;color:#fff;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}}
.card{{max-width:520px;width:100%;background:#141414;border:1px solid #262626;padding:40px;}}
.tag{{font-size:12px;letter-spacing:0.25em;color:#FF3B30;font-weight:bold;margin:0 0 16px 0;}}
h1{{margin:0 0 16px 0;font-size:28px;line-height:1.15;color:{color};font-weight:900;}}
p{{margin:0 0 24px 0;font-size:15px;line-height:1.6;color:#A3A3A3;}}
a.btn{{background:#FF3B30;color:#fff;text-decoration:none;font-weight:bold;letter-spacing:0.05em;padding:14px 28px;display:inline-block;}}
</style>
</head>
<body>
<div class="card">
<p class="tag">GAME ON MOFOS!</p>
<h1>{result['title']}</h1>
<p>{result['message']}</p>
<a class="btn" href="{cta_url}">{'OPEN GOMOFOS' if result['status'] != 'ok' else 'BACK TO GOMOFOS'}</a>
</div>
</body>
</html>"""
    return HTMLResponse(content=page)


@api_router.post("/challenges/{tournament_id}/decline")
async def decline_challenge_authenticated(tournament_id: str, user: dict = Depends(get_current_user)):
    """In-app decline by the invited player. Same effect as the email one-click link."""
    try:
        tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    except Exception:
        tournament = None
    if not tournament:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if user["id"] not in (tournament.get("invited_user_ids") or []):
        raise HTTPException(status_code=403, detail="Only the invited player can decline this challenge")

    # Reuse the same core logic by minting a short-lived token for self
    token = create_decline_token(tournament_id, user["id"])
    result = await _decline_challenge_core(token)
    if result["status"] not in ("ok", "already"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@api_router.get("/challenges/incoming")
async def get_incoming_challenges(user: dict = Depends(get_current_user)):
    """Get private tournaments where current user is invited but hasn't joined yet."""
    # Find private tournaments where user is invited
    tournaments = await db.tournaments.find({
        "is_private": True,
        "invited_user_ids": user["id"],
        "status": "open"
    }).to_list(100)
    
    results = []
    for t in tournaments:
        # Skip if user already joined
        joined = await db.tournament_participants.find_one({"tournament_id": str(t["_id"]), "user_id": user["id"]})
        if joined:
            continue
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])})
        creator = await db.users.find_one({"_id": ObjectId(t["creator_id"])})
        results.append({
            "tournament_id": str(t["_id"]),
            "game_name": game["name"] if game else "Unknown",
            "game_platform": game["platform"] if game else "Unknown",
            "challenger_username": creator["username"] if creator else "Unknown",
            "stake_amount": t["stake_amount"],
            "start_time": t["start_time"],
            "created_at": t["created_at"],
        })
    return results

# Game endpoints
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
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if user_doc.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from games_data import TOP_GAMES
    
    # Build set of existing game names (lowercased) once
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

# Tournament endpoints
@api_router.post("/tournaments", response_model=TournamentResponse)
async def create_tournament(tournament_data: TournamentCreate, user: dict = Depends(get_current_user)):
    if tournament_data.stake_amount <= 0:
        raise HTTPException(status_code=400, detail="Stake amount must be greater than 0")
    
    game = await db.games.find_one({"_id": ObjectId(tournament_data.game_id)})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    user_data = await db.users.find_one({"_id": ObjectId(user["id"])})
    if user_data.get("wallet_balance", 0.0) < tournament_data.stake_amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    # Deduct stake from creator's wallet
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -tournament_data.stake_amount}})
    
    tournament_doc = {
        "game_id": tournament_data.game_id,
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
    
    # Add creator as participant
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
async def get_tournaments(status: Optional[str] = None, current: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    
    tournaments = await db.tournaments.find(query).to_list(1000)
    result = []
    
    for t in tournaments:
        # Hide private tournaments from non-invitees (unless they're the creator)
        if t.get("is_private"):
            if current["id"] != t["creator_id"] and current["id"] not in (t.get("invited_user_ids") or []):
                continue
        game = await db.games.find_one({"_id": ObjectId(t["game_id"])})
        creator = await db.users.find_one({"_id": ObjectId(t["creator_id"])})
        result.append(TournamentResponse(
            id=str(t["_id"]),
            game_id=t["game_id"],
            game_name=game["name"] if game else "Unknown",
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
    
    # If private tournament, must be invited
    if tournament.get("is_private"):
        if user["id"] != tournament["creator_id"] and user["id"] not in (tournament.get("invited_user_ids") or []):
            raise HTTPException(status_code=403, detail="This is a private tournament — you must be invited")
    
    # Check if already joined
    existing = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already joined")
    
    user_data = await db.users.find_one({"_id": ObjectId(user["id"])})
    if user_data.get("wallet_balance", 0.0) < tournament["stake_amount"]:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    # Deduct stake
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": -tournament["stake_amount"]}})
    
    # Add participant
    await db.tournament_participants.insert_one({
        "tournament_id": tournament_id,
        "user_id": user["id"],
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "result_status": "pending"
    })
    
    # Update tournament — auto start when full
    new_count = tournament["current_players"] + 1
    update_fields = {"current_players": new_count}
    if new_count >= tournament["max_players"]:
        update_fields["status"] = "in_progress"
        update_fields["started_at"] = datetime.now(timezone.utc).isoformat()
    await db.tournaments.update_one({"_id": ObjectId(tournament_id)}, {"$set": update_fields})
    
    return {"message": "Joined tournament successfully"}

async def _award_winner_and_close(tournament_id: str, winner_user_id: str, resolution: str):
    """Helper: pays out winner, updates losers, marks tournament completed."""
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    total_pool = tournament["stake_amount"] * tournament["current_players"]
    platform_fee = total_pool * 0.05
    winner_amount = total_pool - platform_fee
    
    await db.users.update_one({"_id": ObjectId(winner_user_id)}, {"$inc": {"wallet_balance": winner_amount, "total_wins": 1}})
    await db.wallet_transactions.insert_one({
        "user_id": winner_user_id,
        "amount": winner_amount,
        "type": "credit",
        "reference_type": "tournament_win",
        "reference_id": tournament_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(1000)
    for p in participants:
        if p["user_id"] != winner_user_id:
            await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"total_losses": 1}})
    
    await db.tournaments.update_one(
        {"_id": ObjectId(tournament_id)},
        {"$set": {"status": "completed", "winner_id": winner_user_id, "resolution": resolution, "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    return winner_amount

@api_router.post("/tournaments/{tournament_id}/submit-result")
async def submit_result(tournament_id: str, claimed_winner_id: str, user: dict = Depends(get_current_user)):
    """Each participant submits who they believe won. When all participants submit, the system checks for agreement."""
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament["status"] not in ("in_progress", "pending_confirmation"):
        raise HTTPException(status_code=400, detail="Tournament is not awaiting results")
    
    # Must be participant
    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    if not participant:
        raise HTTPException(status_code=403, detail="Only participants can submit results")
    
    # Claimed winner must also be a participant
    winner_check = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": claimed_winner_id})
    if not winner_check:
        raise HTTPException(status_code=400, detail="Claimed winner must be a tournament participant")
    
    # Record this player's claim
    await db.tournament_participants.update_one(
        {"tournament_id": tournament_id, "user_id": user["id"]},
        {"$set": {"claimed_winner_id": claimed_winner_id, "result_submitted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Mark tournament as pending_confirmation
    if tournament["status"] == "in_progress":
        await db.tournaments.update_one({"_id": ObjectId(tournament_id)}, {"$set": {"status": "pending_confirmation"}})
    
    # Check if everyone has submitted
    all_participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(1000)
    submitted = [p for p in all_participants if p.get("claimed_winner_id")]
    
    if len(submitted) < len(all_participants):
        return {"message": "Result submitted, waiting for other player(s)", "status": "pending_confirmation"}
    
    # All submitted — check agreement
    claims = set(p["claimed_winner_id"] for p in submitted)
    if len(claims) == 1:
        # Everyone agrees
        winner_id = claims.pop()
        winner_amount = await _award_winner_and_close(tournament_id, winner_id, "auto_agreement")
        return {"message": "Tournament completed (all players agreed)", "status": "completed", "winner_id": winner_id, "winner_amount": winner_amount}
    else:
        # Dispute — capture latency tie-breaker advantage and notify the opponent(s) of the opener
        advantage = await _compute_latency_advantage(tournament_id)
        await db.tournaments.update_one(
            {"_id": ObjectId(tournament_id)},
            {"$set": {
                "status": "disputed",
                "disputed_at": datetime.now(timezone.utc).isoformat(),
                "latency_advantage": advantage,  # {user_id, avg_ms, breakdown} or None
            }}
        )
        # Notify the OTHER participants that the current user just opened a dispute
        opener_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
        opener_username = opener_doc.get("username", "An opponent") if opener_doc else "An opponent"
        game = await db.games.find_one({"_id": ObjectId(tournament["game_id"])}) if tournament.get("game_id") else None
        game_name = game["name"] if game else "your match"
        pot = float(tournament.get("stake_amount", 0)) * len(all_participants)
        app_url = os.environ.get("FRONTEND_URL", "https://gomofos.com")
        for p in all_participants:
            if p["user_id"] == user["id"]:
                continue
            opponent_doc = await db.users.find_one({"_id": ObjectId(p["user_id"])})
            if opponent_doc and opponent_doc.get("email"):
                asyncio.create_task(send_dispute_alert(
                    to_email=opponent_doc["email"],
                    opponent_username=opponent_doc.get("username", "Mofo"),
                    opener_username=opener_username,
                    game_name=game_name,
                    stake_amount=pot,
                    tournament_id=tournament_id,
                    app_url=app_url,
                ))
        return {"message": "Players disagreed on winner — dispute created", "status": "disputed", "latency_advantage": advantage}

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
    winner_amount = await _award_winner_and_close(tournament_id, winner_user_id, resolution)
    
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
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "gomofos"
_storage_key = None

def init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    emergent_key = os.environ.get("EMERGENT_LLM_KEY")
    if not emergent_key:
        raise RuntimeError("EMERGENT_LLM_KEY not set")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": emergent_key}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    if resp.status_code == 403:
        global _storage_key
        _storage_key = None
        key = init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120
        )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 403:
        global _storage_key
        _storage_key = None
        key = init_storage()
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

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

# ============ HIGHLIGHT REELS ============
HIGHLIGHT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
HIGHLIGHT_MAX_DURATION_SEC = 60
HIGHLIGHT_ALLOWED_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


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


# ============ TOURNAMENT SHARE CARD (OG meta for X/Twitter) ============
def _absolute_base_url() -> str:
    return os.environ.get("PUBLIC_APP_URL") or os.environ.get("FRONTEND_URL", "https://gomofos.com")


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

    base = _absolute_base_url().rstrip("/")
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


# ============ LATENCY TRACKING ============
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


# Latency policy thresholds (single source of truth for backend + dispute logic)
LATENCY_WARN_MS = 100
LATENCY_HIGH_MS = 200


async def _compute_latency_advantage(tournament_id: str):
    """Aggregate latency samples per participant and return a dispute-tie-breaker payload.

    Result shape:
      {
        "advantage_user_id": <str or None>,   # lower-latency player (winner of tie-break)
        "policy": "lower_avg_ms_wins_ties",
        "breakdown": [
            {"user_id", "username", "avg_ms", "max_ms", "sample_count", "status"},
            ...
        ],
      }
    A player is only considered for advantage if they have at least 3 samples.
    """
    samples = await db.tournament_latency.find({"tournament_id": tournament_id}).to_list(10000)
    if not samples:
        return {"advantage_user_id": None, "policy": "lower_avg_ms_wins_ties", "breakdown": []}

    by_user: Dict[str, list] = {}
    for s in samples:
        by_user.setdefault(s["user_id"], []).append(float(s["latency_ms"]))

    breakdown = []
    for uid, vals in by_user.items():
        avg = sum(vals) / len(vals)
        peak = max(vals)
        if peak >= LATENCY_HIGH_MS:
            status = "high"
        elif avg >= LATENCY_WARN_MS:
            status = "warn"
        else:
            status = "ok"
        u = await db.users.find_one({"_id": ObjectId(uid)})
        breakdown.append({
            "user_id": uid,
            "username": u.get("username") if u else "Unknown",
            "avg_ms": round(avg, 1),
            "max_ms": round(peak, 1),
            "sample_count": len(vals),
            "status": status,
        })

    eligible = [b for b in breakdown if b["sample_count"] >= 3]
    advantage_user_id = None
    if len(eligible) >= 2:
        # Lower avg wins the tie-break; if anyone is "high", the OTHER side wins by default.
        high_players = [b for b in eligible if b["status"] == "high"]
        low_players = [b for b in eligible if b["status"] != "high"]
        if high_players and low_players and len(high_players) < len(eligible):
            # Pick the best (lowest-avg) non-high player as the tie-break beneficiary
            advantage_user_id = min(low_players, key=lambda b: b["avg_ms"])["user_id"]
        else:
            advantage_user_id = min(eligible, key=lambda b: b["avg_ms"])["user_id"]

    return {"advantage_user_id": advantage_user_id, "policy": "lower_avg_ms_wins_ties", "breakdown": breakdown}


@api_router.get("/tournaments/{tournament_id}/latency-advantage")
async def get_latency_advantage(tournament_id: str, user: dict = Depends(get_current_user)):
    """Return the per-tournament latency tie-breaker payload (used by admins reviewing disputes)."""
    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user["id"]})
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not participant and (not user_doc or user_doc.get("role") != "admin"):
        raise HTTPException(status_code=403, detail="Only participants or admins can view this")
    return await _compute_latency_advantage(tournament_id)

@api_router.get("/tournaments/{tournament_id}/latency")
async def get_latency_history(tournament_id: str, user: dict = Depends(get_current_user)):
    """Get latency timeline for all participants of a tournament (for dispute review)."""
    samples = await db.tournament_latency.find({"tournament_id": tournament_id}).sort("timestamp", 1).to_list(10000)
    
    # Group by user
    by_user: Dict[str, list] = {}
    for s in samples:
        by_user.setdefault(s["user_id"], []).append({"latency_ms": s["latency_ms"], "timestamp": s["timestamp"]})
    
    # Attach usernames + summary
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
    
    # Auth via query token (JWT access token)
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
    
    # Must be a participant
    participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": user_id})
    if not participant:
        await websocket.close(code=4403)
        return
    
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                client_ts = message.get("client_ts")
                # Echo back immediately so client can measure RTT
                await websocket.send_json({"type": "pong", "client_ts": client_ts, "server_ts": int(datetime.now(timezone.utc).timestamp() * 1000)})
            elif message.get("type") == "report":
                # Client reports its measured RTT
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

# Chat endpoints
@api_router.post("/chat", response_model=ChatMessageResponse)
async def send_message(msg_data: ChatMessageCreate, user: dict = Depends(get_current_user)):
    # Validate user is a participant
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

# Wallet/Payment endpoints
@api_router.post("/wallet/daily-bonus")
async def claim_daily_bonus(user: dict = Depends(get_current_user)):
    """Play-money mode: claim a free credit bonus once every 24 hours."""
    DAILY_BONUS = 250.0
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    last_claim_str = user_doc.get("last_daily_bonus")
    now = datetime.now(timezone.utc)
    
    if last_claim_str:
        last_claim = datetime.fromisoformat(last_claim_str)
        if last_claim.tzinfo is None:
            last_claim = last_claim.replace(tzinfo=timezone.utc)
        hours_since = (now - last_claim).total_seconds() / 3600
        if hours_since < 24:
            hours_remaining = 24 - hours_since
            raise HTTPException(
                status_code=400,
                detail=f"Daily bonus already claimed. Try again in {int(hours_remaining)}h {int((hours_remaining % 1) * 60)}m."
            )
    
    # Credit the bonus
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$inc": {"wallet_balance": DAILY_BONUS}, "$set": {"last_daily_bonus": now.isoformat()}}
    )
    await db.wallet_transactions.insert_one({
        "user_id": user["id"],
        "amount": DAILY_BONUS,
        "type": "credit",
        "reference_type": "daily_bonus",
        "reference_id": user["id"],
        "timestamp": now.isoformat()
    })
    
    return {"message": "Daily bonus claimed!", "amount": DAILY_BONUS, "new_balance": user_doc.get("wallet_balance", 0.0) + DAILY_BONUS}

@api_router.get("/wallet/daily-bonus/status")
async def daily_bonus_status(user: dict = Depends(get_current_user)):
    """Check if user can claim daily bonus right now."""
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    last_claim_str = user_doc.get("last_daily_bonus")
    
    if not last_claim_str:
        return {"can_claim": True, "hours_remaining": 0}
    
    last_claim = datetime.fromisoformat(last_claim_str)
    if last_claim.tzinfo is None:
        last_claim = last_claim.replace(tzinfo=timezone.utc)
    hours_since = (datetime.now(timezone.utc) - last_claim).total_seconds() / 3600
    
    if hours_since >= 24:
        return {"can_claim": True, "hours_remaining": 0}
    return {"can_claim": False, "hours_remaining": round(24 - hours_since, 1)}

@api_router.post("/wallet/deposit")
async def create_deposit(req: DepositRequest, user: dict = Depends(get_current_user)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    
    stripe_key = os.environ.get("STRIPE_API_KEY")
    base_url = req.origin_url
    webhook_url = f"{base_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url=webhook_url)
    
    success_url = f"{base_url}/wallet?session_id={{{{CHECKOUT_SESSION_ID}}}}"
    cancel_url = f"{base_url}/wallet"
    
    checkout_request = CheckoutSessionRequest(
        amount=req.amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user["id"], "type": "deposit"}
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction
    await db.payment_transactions.insert_one({
        "user_id": user["id"],
        "session_id": session.session_id,
        "amount": req.amount,
        "currency": "usd",
        "type": "deposit",
        "status": "pending",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"checkout_url": session.url, "session_id": session.session_id}

@api_router.get("/wallet/deposit/status/{session_id}")
async def check_deposit_status(session_id: str, user: dict = Depends(get_current_user)):
    # Check if already processed
    transaction = await db.payment_transactions.find_one({"session_id": session_id, "user_id": user["id"]})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction["payment_status"] == "paid":
        return {"status": "completed", "amount": transaction["amount"]}
    
    # Check with Stripe
    stripe_key = os.environ.get("STRIPE_API_KEY")
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url="")
    
    checkout_status = await stripe_checkout.get_checkout_status(session_id)
    
    if checkout_status.payment_status == "paid" and transaction["payment_status"] != "paid":
        # Credit user wallet
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": transaction["amount"]}})
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"payment_status": "paid", "status": "completed"}})
        
        # Create wallet transaction
        await db.wallet_transactions.insert_one({
            "user_id": user["id"],
            "amount": transaction["amount"],
            "type": "credit",
            "reference_type": "deposit",
            "reference_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {"status": "completed", "amount": transaction["amount"]}
    
    return {"status": checkout_status.status, "payment_status": checkout_status.payment_status}

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    stripe_key = os.environ.get("STRIPE_API_KEY")
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url="")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, request.headers.get("Stripe-Signature"))
        return {"status": "success"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error"}

@api_router.get("/wallet/transactions")
async def get_wallet_transactions(user: dict = Depends(get_current_user)):
    transactions = await db.wallet_transactions.find({"user_id": user["id"]}).sort("timestamp", -1).to_list(100)
    return [{"id": str(t["_id"]), "amount": t["amount"], "type": t["type"], "reference_type": t["reference_type"], "timestamp": t["timestamp"]} for t in transactions]

# Leaderboard
@api_router.get("/leaderboard")
async def get_leaderboard():
    users = await db.users.find({}, {"_id": 1, "username": 1, "total_wins": 1, "total_losses": 1, "wallet_balance": 1}).sort("total_wins", -1).limit(50).to_list(50)
    return [{"user_id": str(u["_id"]), "username": u["username"], "wins": u.get("total_wins", 0), "losses": u.get("total_losses", 0), "balance": u.get("wallet_balance", 0.0)} for u in users]

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get('FRONTEND_URL', 'http://localhost:3000')],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup
@app.on_event("startup")
async def startup_event():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.highlight_reels.create_index([("user_id", 1), ("created_at", -1)])
    await db.highlight_reels.create_index("id", unique=True)
    await db.tournament_latency.create_index([("tournament_id", 1), ("user_id", 1), ("timestamp", 1)])
    
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@esportsbet.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({"email": admin_email, "password_hash": hashed, "username": "Admin", "role": "admin", "wallet_balance": 0.0, "total_wins": 0, "total_losses": 0, "rank": 0, "created_at": datetime.now(timezone.utc).isoformat()})
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
    
    # Init object storage
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()