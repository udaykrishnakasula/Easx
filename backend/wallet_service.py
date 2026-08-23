"""Wallet + immutable ledger service.

Invariants:
- Backend is the sole source of truth for balances.
- Every mutation writes an append-only wallet_transactions (ledger) entry.
- All amounts are Decimal128 (exact). Never float.
- Idempotent: a repeated idempotency_key never double-applies.
- Atomic per-wallet via optimistic version check + retry.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from db import db
from money import d128, fmt, to_dec

_MAX_RETRIES = 8


class InsufficientBalance(HTTPException):
    def __init__(self, required, available):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "insufficient_balance",
                "message": "Insufficient wallet balance.",
                "required": fmt(required),
                "available": fmt(available),
            },
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_or_create_wallet(user_id: str) -> dict:
    wallet = await db.wallets.find_one({"user_id": user_id})
    if wallet:
        return wallet
    ts = _now()
    wallet = {
        "id": str(uuid.uuid4()), "user_id": user_id, "currency": "USDT",
        "available_balance": d128(0), "total_invested": d128(0),
        "total_earned": d128(0), "version": 0,
        "created_at": ts, "updated_at": ts,
    }
    try:
        await db.wallets.insert_one(wallet)
    except DuplicateKeyError:
        wallet = await db.wallets.find_one({"user_id": user_id})
    return wallet


async def _find_tx_by_key(key):
    if not key:
        return None
    return await db.wallet_transactions.find_one({"idempotency_key": key})


async def _apply(user_id, amount, direction, tx_type, ref_type, ref_id,
                idempotency_key, note, extra_wallet_inc=None):
    """Core credit/debit. amount is positive Decimal. direction credit|debit."""
    amount = to_dec(amount)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive.")

    # Idempotent replay
    existing = await _find_tx_by_key(idempotency_key)
    if existing:
        return existing

    wallet = await get_or_create_wallet(user_id)

    # Early friendly balance check for debits
    if direction == "debit" and to_dec(wallet["available_balance"]) < amount:
        raise InsufficientBalance(amount, wallet["available_balance"])

    # Insert ledger lock first (idempotency key is unique) with placeholder balance_after.
    tx_id = str(uuid.uuid4())
    tx_doc = {
        "id": tx_id, "wallet_id": wallet["id"], "user_id": user_id,
        "type": tx_type, "direction": direction,
        "amount": d128(amount), "balance_after": d128(0),
        "ref_type": ref_type, "ref_id": ref_id,
        "status": "pending", "idempotency_key": idempotency_key,
        "note": note, "created_at": _now(), "created_by": user_id,
    }
    try:
        await db.wallet_transactions.insert_one(tx_doc)
    except DuplicateKeyError:
        prior = await _find_tx_by_key(idempotency_key)
        if prior:
            return prior
        raise

    # Version-guarded wallet update with retry.
    balance_after = None
    for _ in range(_MAX_RETRIES):
        w = await db.wallets.find_one({"user_id": user_id})
        cur = to_dec(w["available_balance"])
        if direction == "debit":
            if cur < amount:
                await db.wallet_transactions.delete_one({"id": tx_id})
                raise InsufficientBalance(amount, cur)
            new_bal = cur - amount
        else:
            new_bal = cur + amount

        inc_fields = {}
        if extra_wallet_inc:
            for k, v in extra_wallet_inc.items():
                inc_fields[k] = to_dec(w.get(k, 0)) + to_dec(v)

        set_doc = {"available_balance": d128(new_bal), "updated_at": _now()}
        for k, v in inc_fields.items():
            set_doc[k] = d128(v)
        res = await db.wallets.update_one(
            {"user_id": user_id, "version": w["version"]},
            {"$set": set_doc, "$inc": {"version": 1}},
        )
        if res.modified_count == 1:
            balance_after = new_bal
            break
    if balance_after is None:
        await db.wallet_transactions.delete_one({"id": tx_id})
        raise HTTPException(status_code=409, detail="Wallet busy, please retry.")

    await db.wallet_transactions.update_one(
        {"id": tx_id},
        {"$set": {"balance_after": d128(balance_after), "status": "completed"}},
    )
    tx_doc["balance_after"] = d128(balance_after)
    tx_doc["status"] = "completed"
    return tx_doc


async def credit(user_id, amount, tx_type, ref_type=None, ref_id=None,
                 idempotency_key=None, note=None, inc=None):
    return await _apply(user_id, amount, "credit", tx_type, ref_type, ref_id,
                        idempotency_key, note, extra_wallet_inc=inc)


async def debit(user_id, amount, tx_type, ref_type=None, ref_id=None,
                idempotency_key=None, note=None, inc=None):
    return await _apply(user_id, amount, "debit", tx_type, ref_type, ref_id,
                        idempotency_key, note, extra_wallet_inc=inc)


def serialize_wallet(w: dict) -> dict:
    return {
        "currency": w.get("currency", "USDT"),
        "available_balance": fmt(w["available_balance"]),
        "total_invested": fmt(w.get("total_invested", 0)),
        "total_earned": fmt(w.get("total_earned", 0)),
    }


async def compute_locked(user_id: str):
    """Money currently inside ACTIVE investments (sum of active principals)."""
    total = to_dec(0)
    async for inv in db.investments.find(
        {"user_id": user_id, "status": "active"}, {"principal": 1}
    ):
        total += to_dec(inv["principal"])
    return total


async def wallet_summary(user_id: str) -> dict:
    """Three balances: Available, Locked Investment, Total Portfolio."""
    w = await get_or_create_wallet(user_id)
    available = to_dec(w["available_balance"])
    locked = await compute_locked(user_id)
    return {
        "currency": w.get("currency", "USDT"),
        "available_balance": fmt(available),
        "locked_investment": fmt(locked),
        "total_portfolio": fmt(available + locked),
        "total_invested": fmt(w.get("total_invested", 0)),
        "total_earned": fmt(w.get("total_earned", 0)),
    }


async def check_consistency(user_id: str) -> dict:
    """Assert available_balance == sum(ledger credits) - sum(ledger debits).
    Every available-balance change is ledgered, so these must match exactly."""
    w = await get_or_create_wallet(user_id)
    ledger = to_dec(0)
    async for t in db.wallet_transactions.find(
        {"user_id": user_id, "status": "completed"}, {"amount": 1, "direction": 1}
    ):
        amt = to_dec(t["amount"])
        ledger += amt if t["direction"] == "credit" else -amt
    available = to_dec(w["available_balance"])
    return {
        "user_id": user_id,
        "available_balance": fmt(available),
        "ledger_balance": fmt(ledger),
        "consistent": available == ledger,
    }


def serialize_tx(t: dict) -> dict:
    return {
        "id": t["id"], "type": t["type"], "direction": t["direction"],
        "amount": fmt(t["amount"]), "balance_after": fmt(t.get("balance_after", 0)),
        "ref_type": t.get("ref_type"), "ref_id": t.get("ref_id"),
        "status": t.get("status"), "note": t.get("note"),
        "created_at": t.get("created_at"),
    }


async def list_transactions(user_id: str, limit: int = 50, skip: int = 0):
    cur = db.wallet_transactions.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    return [serialize_tx(t) async for t in cur]


# Transaction types that represent rewards (money earned) or payouts (money out)
# surfaced in the live activity feed on the dashboard.
REWARD_FEED_TYPES = [
    "PROFIT",               # investment profit at maturity
    "INVESTMENT_MATURITY",  # principal returned at maturity
    "REFERRAL_COMMISSION",  # referral earnings
    "WITHDRAWAL",           # payout to external address
]


def feed_category(tx_type: str) -> str:
    """Classify a ledger entry for the live feed."""
    if tx_type in ("PROFIT", "REFERRAL_COMMISSION"):
        return "reward"
    if tx_type == "INVESTMENT_MATURITY":
        return "maturity"
    if tx_type == "WITHDRAWAL":
        return "payout"
    return "other"


async def list_rewards_feed(user_id: str, limit: int = 30, since: str | None = None):
    """Return recent reward/payout ledger entries for the live activity feed.

    `since` (ISO timestamp) enables incremental polling: only entries created
    strictly after it are returned, so the client can append new items.
    """
    query = {"user_id": user_id, "type": {"$in": REWARD_FEED_TYPES}}
    if since:
        query["created_at"] = {"$gt": since}
    cur = db.wallet_transactions.find(query).sort("created_at", -1).limit(limit)
    items = []
    async for t in cur:
        tx = serialize_tx(t)
        tx["category"] = feed_category(t["type"])
        items.append(tx)
    return items
