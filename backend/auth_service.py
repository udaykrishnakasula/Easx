"""Auth domain logic: registration, authentication, admin seed, indexes.

Backend is the source of truth. All uniqueness (email, phone, referral_code)
is enforced by unique indexes AND checked here for friendly errors.
"""
import os
import secrets
import string
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from bson.decimal128 import Decimal128
from fastapi import HTTPException, status
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from db import db
from security import hash_password, verify_password

REQUIRE_EMAIL_VERIFICATION = os.environ.get("REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"
_REF_ALPHABET = string.ascii_uppercase + string.digits


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_indexes() -> None:
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index([("phone", ASCENDING)], unique=True)
    await db.users.create_index([("referral_code", ASCENDING)], unique=True)


async def _generate_referral_code() -> str:
    for _ in range(10):
        code = "".join(secrets.choice(_REF_ALPHABET) for _ in range(8))
        if not await db.users.find_one({"referral_code": code}):
            return code
    return uuid.uuid4().hex[:10].upper()


def public_user(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return doc


async def register_user(name: str, email: str, phone: str, password: str, referral_code=None) -> dict:
    email = email.strip().lower()
    phone = phone.strip()

    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")
    if await db.users.find_one({"phone": phone}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number is already registered.")

    referred_by = None
    if referral_code:
        referrer = await db.users.find_one({"referral_code": referral_code})
        if not referrer:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid referral code.")
        referred_by = referrer["id"]

    user = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "email": email,
        "phone": phone,
        "password_hash": hash_password(password),
        "role": "user",
        "email_verified": not REQUIRE_EMAIL_VERIFICATION,
        "kyc_status": "none",
        "status": "active",
        "referral_code": await _generate_referral_code(),
        "referred_by": referred_by,
        "created_at": _now_iso(),
        "last_login_at": None,
    }
    try:
        await db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or phone already registered.")

    # Bootstrap wallet + profile so every user has a wallet (backend source of truth).
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()), "user_id": user["id"], "currency": "USDT",
            "available_balance": Decimal128(Decimal("0")),
            "total_invested": Decimal128(Decimal("0")),
            "total_earned": Decimal128(Decimal("0")),
            "version": 0, "created_at": user["created_at"], "updated_at": user["created_at"],
        }},
        upsert=True,
    )
    await db.user_profiles.update_one(
        {"user_id": user["id"]},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()), "user_id": user["id"], "full_name": user["name"],
            "created_at": user["created_at"], "updated_at": user["created_at"],
        }},
        upsert=True,
    )

    # Record the direct (level-1) referral relationship. Unique on referee_id
    # guarantees at most one referrer per user (no duplicate relationships).
    if referred_by:
        try:
            await db.referrals.insert_one({
                "id": str(uuid.uuid4()),
                "referrer_id": referred_by,
                "referee_id": user["id"],
                "level": 1,
                "created_at": user["created_at"],
            })
        except DuplicateKeyError:
            pass

    return user


async def authenticate_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if user.get("status") in ("banned", "suspended"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been suspended. Please contact support.")
    if REQUIRE_EMAIL_VERIFICATION and not user.get("email_verified", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in.")
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login_at": _now_iso()}})
    return user


async def seed_admin() -> None:
    email = os.environ.get("ADMIN_EMAIL", "admin@easyx.com").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "Admin@Easyx2026")
    name = os.environ.get("ADMIN_NAME", "EasyX Admin")
    phone = os.environ.get("ADMIN_PHONE", "+910000000001").strip()

    existing = await db.users.find_one({"email": email})
    if existing:
        if existing.get("role") != "admin":
            await db.users.update_one({"id": existing["id"]}, {"$set": {"role": "admin"}})
        return

    admin = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "phone": phone,
        "password_hash": hash_password(password),
        "role": "admin",
        "email_verified": True,
        "kyc_status": "none",
        "status": "active",
        "referral_code": await _generate_referral_code(),
        "referred_by": None,
        "created_at": _now_iso(),
        "last_login_at": None,
    }
    try:
        await db.users.insert_one(admin)
    except DuplicateKeyError:
        pass
