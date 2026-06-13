"""Referral program: invite + list mine."""
import asyncio
import os
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException

from core import api_router, db, logger, get_current_user, REFERRAL_BONUS
from models import ReferralInvite


@api_router.post("/referrals/invite")
async def send_referral_invite(payload: ReferralInvite, user: dict = Depends(get_current_user)):
    email = (payload.email or "").strip().lower()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Enter a valid email")
    if email == (user.get("email") or "").lower():
        raise HTTPException(status_code=400, detail="That's your own email")
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="That email is already on Gomofos")
    rec = await db.referrals.find_one({"referrer_id": user["id"], "invitee_email": email})
    if not rec:
        rec = {
            "id": str(uuid.uuid4()),
            "referrer_id": user["id"],
            "referrer_username": user.get("username"),
            "invitee_email": email,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.referrals.insert_one(rec)
    app_url = os.environ.get("FRONTEND_URL", "https://gomofos.com").rstrip("/")
    signup_url = f"{app_url}/register?ref={rec['id']}"
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if api_key:
        try:
            from email_service import send_email_async, _wrap_html
            html = _wrap_html(
                f"{user.get('username')} wants you on Gomofos",
                f"<strong>{user.get('username')}</strong> just challenged you to join GOMOFOS — the esports staking platform where you bet on yourself.",
                signup_url, "ACCEPT THE CHALLENGE",
                f"<p style='font-size:13px;color:#A3A3A3;margin-top:16px'>You'll get 1,000 free credits when you sign up. If you use the link above, <strong>{user.get('username')}</strong> also earns {int(REFERRAL_BONUS)} CR.</p>"
            )
            plain = f"{user.get('username')} invited you to Gomofos. Sign up: {signup_url}"
            asyncio.create_task(send_email_async(email, f"{user.get('username')} challenged you on Gomofos", html, plain))
        except Exception as e:
            logger.warning(f"Referral email failed: {e}")
    return {"invite_id": rec["id"], "invite_url": signup_url, "status": "sent" if api_key else "queued_no_sendgrid"}


@api_router.get("/referrals/mine")
async def list_my_referrals(user: dict = Depends(get_current_user)):
    items = await db.referrals.find({"referrer_id": user["id"]}).sort("created_at", -1).to_list(500)
    return {
        "bonus_per_signup": REFERRAL_BONUS,
        "total_earned": sum(REFERRAL_BONUS for r in items if r.get("status") == "credited"),
        "referrals": [
            {"id": r["id"], "invitee_email": r["invitee_email"], "status": r.get("status"),
             "created_at": r.get("created_at"), "signed_up_at": r.get("signed_up_at")}
            for r in items
        ],
    }
