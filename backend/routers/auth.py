"""Auth + admin 2FA routes."""
import os
import secrets
from datetime import datetime, timezone, timedelta

import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException, Request, Response

from core import (
    api_router, db, logger, JWT_ALGORITHM,
    get_current_user, get_jwt_secret, hash_password, verify_password,
    create_access_token, create_refresh_token,
    WELCOME_BONUS, REFERRAL_BONUS,
    TWOFA_MAX_ATTEMPTS,
)
from models import (
    UserRegister, UserLogin, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest, TwoFAChallenge,
)
from services import start_admin_2fa


@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserRegister, response: Response):
    email = user_data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user_data.password)
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

    # Process referral if provided
    if user_data.ref:
        ref = await db.referrals.find_one({"id": user_data.ref, "status": "pending"})
        if ref and ref["referrer_id"] != user_id:
            await db.users.update_one(
                {"_id": ObjectId(ref["referrer_id"])},
                {"$inc": {"wallet_balance": REFERRAL_BONUS}}
            )
            await db.wallet_transactions.insert_one({
                "user_id": ref["referrer_id"],
                "amount": REFERRAL_BONUS,
                "type": "credit",
                "reference_type": "referral_bonus",
                "reference_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            await db.referrals.update_one(
                {"id": user_data.ref},
                {"$set": {
                    "status": "credited",
                    "invitee_user_id": user_id,
                    "signed_up_at": datetime.now(timezone.utc).isoformat(),
                }}
            )

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
        can_manage_ads=False,
        created_at=user_doc["created_at"]
    )


@api_router.post("/auth/login")
async def login(credentials: UserLogin, request: Request, response: Response):
    email = credentials.email.lower()
    ip = request.client.host
    identifier = f"{ip}:{email}"

    attempt_doc = await db.login_attempts.find_one({"identifier": identifier})
    if attempt_doc and attempt_doc.get("count", 0) >= 5:
        lockout_until = attempt_doc.get("locked_until")
        # MongoDB returns tz-naive datetimes; normalise to UTC-aware for comparison.
        if lockout_until is not None and lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=timezone.utc)
        if lockout_until and datetime.now(timezone.utc) < lockout_until:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        if attempt_doc:
            new_count = attempt_doc.get("count", 0) + 1
            update_data = {"count": new_count}
            if new_count >= 5:
                update_data["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=15)
            await db.login_attempts.update_one({"identifier": identifier}, {"$set": update_data})
        else:
            await db.login_attempts.insert_one({"identifier": identifier, "count": 1})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await db.login_attempts.delete_one({"identifier": identifier})

    # ADMIN 2FA gate — admins must complete a WhatsApp code challenge before getting a session
    if user.get("role") == "admin" and (user.get("whatsapp_phone") or "").strip():
        return await start_admin_2fa(user, response)

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
        status=user.get("status") or "active",
        on_hold_reason=user.get("on_hold_reason"),
        dispute_stats=user.get("dispute_stats"),
        whatsapp_phone=user.get("whatsapp_phone"),
        can_manage_ads=bool(user.get("can_manage_ads")),
        created_at=user["created_at"]
    )


@api_router.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    fresh = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not fresh:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=str(fresh["_id"]),
        email=fresh["email"],
        username=fresh["username"],
        wallet_balance=fresh.get("wallet_balance", 0.0),
        total_wins=fresh.get("total_wins", 0),
        total_losses=fresh.get("total_losses", 0),
        rank=fresh.get("rank", 0),
        role=fresh.get("role"),
        status=fresh.get("status") or "active",
        on_hold_reason=fresh.get("on_hold_reason"),
        dispute_stats=fresh.get("dispute_stats"),
        whatsapp_phone=fresh.get("whatsapp_phone"),
        can_manage_ads=bool(fresh.get("can_manage_ads")),
        created_at=fresh["created_at"],
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


@api_router.post("/auth/2fa/verify", response_model=UserResponse)
async def verify_2fa(payload: TwoFAChallenge, response: Response):
    chal = await db.twofa_challenges.find_one({"id": payload.challenge_id})
    if not chal:
        raise HTTPException(status_code=400, detail="Invalid or expired challenge")
    expires = datetime.fromisoformat(chal["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        await db.twofa_challenges.delete_one({"id": payload.challenge_id})
        raise HTTPException(status_code=400, detail="Code expired — log in again to get a new code")
    if chal.get("attempts", 0) >= TWOFA_MAX_ATTEMPTS:
        await db.twofa_challenges.delete_one({"id": payload.challenge_id})
        raise HTTPException(status_code=429, detail="Too many attempts. Log in again to get a new code")
    if not verify_password(payload.code.strip(), chal["code_hash"]):
        await db.twofa_challenges.update_one({"id": payload.challenge_id}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="Wrong code")
    user_doc = await db.users.find_one({"_id": ObjectId(chal["user_id"])})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    access_token = create_access_token(str(user_doc["_id"]), user_doc["email"])
    refresh_token = create_refresh_token(str(user_doc["_id"]))
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    await db.twofa_challenges.delete_one({"id": payload.challenge_id})
    return UserResponse(
        id=str(user_doc["_id"]), email=user_doc["email"], username=user_doc["username"],
        wallet_balance=user_doc.get("wallet_balance", 0.0),
        total_wins=user_doc.get("total_wins", 0), total_losses=user_doc.get("total_losses", 0),
        rank=user_doc.get("rank", 0), role=user_doc.get("role"),
        status=user_doc.get("status") or "active",
        on_hold_reason=user_doc.get("on_hold_reason"),
        dispute_stats=user_doc.get("dispute_stats"),
        whatsapp_phone=user_doc.get("whatsapp_phone"),
        can_manage_ads=bool(user_doc.get("can_manage_ads")),
        created_at=user_doc["created_at"],
    )
