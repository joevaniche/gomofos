"""Wallet: daily-bonus (retired), Stripe deposit, transactions, webhook."""
import os
from datetime import datetime, timezone

from bson import ObjectId
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
from fastapi import Depends, HTTPException, Request

from core import api_router, db, get_current_user
from models import DepositRequest


@api_router.post("/wallet/daily-bonus")
async def claim_daily_bonus(user: dict = Depends(get_current_user)):
    """Daily bonus has been retired — players now get their starting credits and must purchase more."""
    raise HTTPException(status_code=410, detail="Daily bonus has been retired. Top up via the Wallet to add credits.")


@api_router.get("/wallet/daily-bonus/status")
async def daily_bonus_status(user: dict = Depends(get_current_user)):
    """Daily bonus retired."""
    return {"can_claim": False, "hours_remaining": 0, "retired": True}


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
    transaction = await db.payment_transactions.find_one({"session_id": session_id, "user_id": user["id"]})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction["payment_status"] == "paid":
        return {"status": "completed", "amount": transaction["amount"]}

    stripe_key = os.environ.get("STRIPE_API_KEY")
    stripe_checkout = StripeCheckout(api_key=stripe_key, webhook_url="")

    checkout_status = await stripe_checkout.get_checkout_status(session_id)

    if checkout_status.payment_status == "paid" and transaction["payment_status"] != "paid":
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"wallet_balance": transaction["amount"]}})
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"payment_status": "paid", "status": "completed"}})

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
