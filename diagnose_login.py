"""
Diagnostic script for the gomofos login issue.

Run on the LIVE server (192.168.0.124) from your backend directory:

    cd /path/to/backend          # the one with server.py + .env
    source venv/bin/activate     # or whichever venv you use
    python diagnose_login.py davidjovanic@yahoo.com.au

It will prompt for the password. Nothing is sent to the network — it queries
your local MongoDB directly and tests bcrypt against the stored hash.
"""
import os
import sys
import getpass
from pathlib import Path
from dotenv import load_dotenv
import bcrypt
from pymongo import MongoClient
from datetime import datetime, timezone

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

mongo_url = os.environ.get("MONGO_URL")
db_name = os.environ.get("DB_NAME")
print(f"MONGO_URL = {mongo_url}")
print(f"DB_NAME   = {db_name}")
if not mongo_url or not db_name:
    print("ERROR: MONGO_URL or DB_NAME missing from .env")
    sys.exit(1)

client = MongoClient(mongo_url)
db = client[db_name]

email = (sys.argv[1] if len(sys.argv) > 1 else input("Email: ")).strip().lower()
print(f"\nSearching for user with email = {email!r}")

user = db.users.find_one({"email": email})
if not user:
    print("\n*** USER NOT FOUND in db.users with that exact email ***")
    print("Let's search case-insensitively to find anything close:")
    import re
    candidates = list(db.users.find({"email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}}))
    print(f"  Case-insensitive matches: {len(candidates)}")
    for c in candidates:
        print(f"   - {c.get('email')!r}  username={c.get('username')!r}")
    print("\nAlso search by username substring:")
    name = email.split("@")[0]
    others = list(db.users.find({"$or": [
        {"username": {"$regex": name, "$options": "i"}},
        {"email": {"$regex": name, "$options": "i"}}
    ]}).limit(10))
    for o in others:
        print(f"   - email={o.get('email')!r}  username={o.get('username')!r}")
    sys.exit(0)

print("\n*** USER FOUND ***")
print(f"  _id            = {user.get('_id')}")
print(f"  email          = {user.get('email')!r}")
print(f"  username       = {user.get('username')!r}")
print(f"  created_at     = {user.get('created_at')}")
print(f"  wallet_balance = {user.get('wallet_balance')}")
pw_hash = user.get("password_hash")
print(f"  password_hash  = {pw_hash!r}")
print(f"  hash type      = {type(pw_hash).__name__}")
print(f"  hash length    = {len(pw_hash) if pw_hash else 'N/A'}")
if pw_hash and isinstance(pw_hash, str):
    print(f"  hash prefix    = {pw_hash[:7]}  (should be $2a$ / $2b$ / $2y$ for bcrypt)")

# Brute force lockout
print("\n--- Brute force lockout check ---")
attempts = list(db.login_attempts.find({"identifier": {"$regex": email, "$options": "i"}}))
if attempts:
    for a in attempts:
        print(f"  identifier={a.get('identifier')!r}  count={a.get('count')}  locked_until={a.get('locked_until')}")
        lu = a.get("locked_until")
        if lu and isinstance(lu, datetime):
            if lu.tzinfo is None:
                lu = lu.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) < lu:
                print(f"  >>> LOCKED until {lu} <<<")
else:
    print("  No failed attempts recorded.")

# Test password
print("\n--- Test password against stored hash ---")
pw = getpass.getpass("Enter the password you've been trying (input hidden): ")
try:
    ok = bcrypt.checkpw(pw.encode("utf-8"), pw_hash.encode("utf-8"))
    print(f"  bcrypt.checkpw result: {ok}")
    if ok:
        print("  >>> PASSWORD MATCHES THE STORED HASH. The bug is elsewhere (API/cookies/network). <<<")
    else:
        print("  >>> PASSWORD DOES NOT MATCH THE STORED HASH. <<<")
        print("  Possible causes:")
        print("    1. The password is genuinely different from what you remember.")
        print("    2. The hash was overwritten (e.g., by a reset, seed re-run, or migration).")
        print("    3. The hash was stored with a different scheme/algorithm.")
except Exception as e:
    print(f"  ERROR running bcrypt.checkpw: {e}")
    print("  This usually means password_hash is not a valid bcrypt hash string.")

client.close()
