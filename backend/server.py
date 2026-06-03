from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
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
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

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
    created_at: str

class GameCreate(BaseModel):
    name: str
    platform: str
    image_url: Optional[str] = None

class GameResponse(BaseModel):
    id: str
    name: str
    platform: str
    image_url: Optional[str]
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

# Game endpoints
@api_router.post("/games", response_model=GameResponse)
async def create_game(game_data: GameCreate, user: dict = Depends(get_current_user)):
    game_doc = {
        "name": game_data.name,
        "platform": game_data.platform,
        "image_url": game_data.image_url,
        "created_by": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.games.insert_one(game_doc)
    return GameResponse(
        id=str(result.inserted_id),
        name=game_doc["name"],
        platform=game_doc["platform"],
        image_url=game_doc["image_url"],
        created_at=game_doc["created_at"]
    )

@api_router.get("/games", response_model=List[GameResponse])
async def get_games():
    games = await db.games.find({}, {"_id": 1, "name": 1, "platform": 1, "image_url": 1, "created_at": 1}).to_list(1000)
    return [GameResponse(
        id=str(g["_id"]),
        name=g["name"],
        platform=g["platform"],
        image_url=g.get("image_url"),
        created_at=g["created_at"]
    ) for g in games]

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
async def get_tournaments(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    
    tournaments = await db.tournaments.find(query).to_list(1000)
    result = []
    
    for t in tournaments:
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
    
    # Update tournament
    new_count = tournament["current_players"] + 1
    await db.tournaments.update_one({"_id": ObjectId(tournament_id)}, {"$set": {"current_players": new_count}})
    
    return {"message": "Joined tournament successfully"}

@api_router.post("/tournaments/{tournament_id}/complete")
async def complete_tournament(tournament_id: str, winner_user_id: str, user: dict = Depends(get_current_user)):
    tournament = await db.tournaments.find_one({"_id": ObjectId(tournament_id)})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament["creator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only creator can complete tournament")
    
    if tournament["status"] != "open":
        raise HTTPException(status_code=400, detail="Tournament already completed")
    
    # Validate winner is a participant
    winner_participant = await db.tournament_participants.find_one({"tournament_id": tournament_id, "user_id": winner_user_id})
    if not winner_participant:
        raise HTTPException(status_code=400, detail="Winner must be a tournament participant")
    
    # Calculate total prize pool
    total_pool = tournament["stake_amount"] * tournament["current_players"]
    platform_fee = total_pool * 0.05  # 5% platform fee
    winner_amount = total_pool - platform_fee
    
    # Award winner
    await db.users.update_one({"_id": ObjectId(winner_user_id)}, {"$inc": {"wallet_balance": winner_amount, "total_wins": 1}})
    
    # Update losers
    participants = await db.tournament_participants.find({"tournament_id": tournament_id}).to_list(1000)
    for p in participants:
        if p["user_id"] != winner_user_id:
            await db.users.update_one({"_id": ObjectId(p["user_id"])}, {"$inc": {"total_losses": 1}})
    
    # Update tournament
    await db.tournaments.update_one({"_id": ObjectId(tournament_id)}, {"$set": {"status": "completed", "winner_id": winner_user_id}})
    
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
            "joined_at": p["joined_at"]
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
        "created_at": tournament["created_at"],
        "participants": participant_list
    }

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
    
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@esportsbet.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({"email": admin_email, "password_hash": hashed, "username": "Admin", "role": "admin", "wallet_balance": 0.0, "total_wins": 0, "total_losses": 0, "rank": 0, "created_at": datetime.now(timezone.utc).isoformat()})
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()