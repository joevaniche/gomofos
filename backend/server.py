"""Gomofos backend entry point.

All routes live in `routers/`. Helpers live in `services.py`. Shared singletons
(app, api_router, db, JWT helpers, get_current_user, constants) live in `core.py`.

This file:
1. Imports every router module so their @api_router decorators fire and register routes.
2. Includes the api_router on the app and mounts CORS middleware.
3. Registers startup/shutdown lifecycle hooks (indexes, admin seed, storage init, reminder loop).
"""
import asyncio
import os
from datetime import datetime, timezone

from starlette.middleware.cors import CORSMiddleware

from core import app, api_router, db, client, logger, hash_password, verify_password
from services import init_storage, reminder_scheduler_loop

# Import every router module so each one registers its routes on api_router at import time.
# Order does not matter — FastAPI dedupes by path+method when including the router.
from routers import auth as _auth  # noqa: F401
from routers import users as _users  # noqa: F401
from routers import challenges as _challenges  # noqa: F401
from routers import games as _games  # noqa: F401
from routers import tournaments as _tournaments  # noqa: F401
from routers import competitions as _competitions  # noqa: F401
from routers import chat as _chat  # noqa: F401
from routers import wallet as _wallet  # noqa: F401
from routers import admin as _admin  # noqa: F401
from routers import prizes as _prizes  # noqa: F401
from routers import highlights as _highlights  # noqa: F401
from routers import referrals as _referrals  # noqa: F401
from routers import misc as _misc  # noqa: F401
from routers import ads as _ads  # noqa: F401
from routers import admin_latency as _admin_latency  # noqa: F401

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get('FRONTEND_URL', 'http://localhost:3000')],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.highlight_reels.create_index([("user_id", 1), ("created_at", -1)])
    await db.highlight_reels.create_index("id", unique=True)
    await db.tournament_latency.create_index([("tournament_id", 1), ("user_id", 1), ("timestamp", 1)])
    # 30-day TTL on latency samples — admin can extend per-match if a dispute is open.
    await db.tournament_latency.create_index("expires_at", expireAfterSeconds=0)
    await db.competition_latency.create_index("expires_at", expireAfterSeconds=0)
    # Backfill expires_at on legacy samples (pre-TTL rows) so the TTL applies retroactively.
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) + timedelta(days=30)
    await db.tournament_latency.update_many({"expires_at": {"$exists": False}}, {"$set": {"expires_at": cutoff}})
    await db.competition_latency.update_many({"expires_at": {"$exists": False}}, {"$set": {"expires_at": cutoff}})
    # Ads indexes
    await db.advertisements.create_index("id", unique=True)
    await db.advertisements.create_index([("active", 1), ("created_at", -1)])
    # Ad analytics events — TTL 90 days
    await db.ad_events.create_index("expires_at", expireAfterSeconds=0)
    await db.ad_events.create_index([("ad_id", 1), ("timestamp", -1)])

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@esportsbet.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "email": admin_email, "password_hash": hashed, "username": "Admin",
            "role": "admin", "wallet_balance": 0.0, "total_wins": 0, "total_losses": 0,
            "rank": 0, "created_at": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )

    # Init object storage
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")

    # Kick off the reminder scheduler in the background
    try:
        asyncio.create_task(reminder_scheduler_loop())
        logger.info("Reminder scheduler started")
    except Exception as e:
        logger.warning(f"Reminder scheduler failed to start: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
