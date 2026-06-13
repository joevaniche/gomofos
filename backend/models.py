"""All Pydantic request/response models for the Gomofos API."""
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
    ref: Optional[str] = None    # referral id from /register?ref=...


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
    status: Optional[str] = None        # "active" (default) or "on_hold"
    on_hold_reason: Optional[str] = None
    dispute_stats: Optional[dict] = None
    whatsapp_phone: Optional[str] = None
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
    platform: str
    stake_amount: float
    max_players: int
    start_time: str


class TournamentResponse(BaseModel):
    id: str
    game_id: str
    game_name: str
    platform: str
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
    whatsapp_phone: Optional[str] = None  # E.164 format e.g. +61412345678 — used for reminders


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


# === HEAD-TO-HEAD COMPETITIONS ===
class CompetitionCreate(BaseModel):
    opponent_user_id: str
    game_id: str
    platform: str
    stake_per_match: float


class CompetitionMatchLog(BaseModel):
    winner_user_id: str   # which side won this match
    notes: Optional[str] = None


# === PRIZES / BLING (images + feat-based unlock) ===
class PrizeFeat(BaseModel):
    type: Optional[str] = None       # tournament_wins | h2h_wins | wins_in_genre | streak | net_credits | streak_in_genre
    count: Optional[int] = None      # threshold value (e.g. 10)
    genre: Optional[str] = None      # for wins_in_genre / streak_in_genre — matches game.category


class PrizeCreate(BaseModel):
    name: str
    cost: float
    image_url: Optional[str] = ""        # large image displayed on the profile
    thumb_url: Optional[str] = ""        # small image shown next to player name on leaderboard
    feat: Optional[PrizeFeat] = None
    # Legacy/optional fields kept for backward-compat with pre-image catalogue
    description: Optional[str] = ""
    kind: Optional[str] = "image"        # always 'image' for new prizes
    asset: Optional[str] = ""
    rarity: Optional[str] = "common"
    active: Optional[bool] = True


class PrizeEquip(BaseModel):
    inventory_id: str


class AdminDisputeResolution(BaseModel):
    kind: str               # "tournament" or "competition_match"
    id: str                 # tournament_id or match_id
    competition_id: Optional[str] = None  # only for competition_match
    winner_user_id: Optional[str] = None  # winner — leave empty to void the match/tournament
    note: Optional[str] = None


class ReferralInvite(BaseModel):
    email: str


class TwoFAChallenge(BaseModel):
    challenge_id: str
    code: str
