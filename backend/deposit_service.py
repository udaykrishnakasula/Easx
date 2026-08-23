"""USDT deposit service (manual verification).

Flow: user picks a network (TRC20/BEP20), sees the EasyX deposit address, enters
the amount they sent and the on-chain transaction hash, and submits. The deposit
is created as PENDING. NO wallet credit happens automatically and blockchain
transactions are NOT auto-verified. An admin manually APPROVES (crediting the
exact approved amount to the Available Wallet) or REJECTS (no credit).

Rules:
- Minimum deposit = $300.
- Duplicate on-chain transaction hashes are rejected (globally unique).
- Investment purchases NEVER create deposits; users fund the wallet here first.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

import notify_service
import wallet_service
from db import db
from money import d128, fmt, to_dec

MIN_DEPOSIT = Decimal("300")
NETWORKS = ["TRC20", "BEP20"]
_PLATFORM_ID = "platform"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_hash(tx_hash: str) -> str:
    return (tx_hash or "").strip().lower()


async def get_platform() -> dict:
    return await db.platform_settings.find_one({"id": _PLATFORM_ID}) or {}


async def get_config() -> dict:
    ps = await get_platform()
    addrs = ps.get("deposit_addresses") or {}
    trc = addrs.get("TRC20")
    bep = addrs.get("BEP20")
    return {
        "currency": ps.get("currency", "USDT"),
        "min_deposit": fmt(MIN_DEPOSIT),
        "networks": NETWORKS,
        "addresses": {"TRC20": trc, "BEP20": bep},
        "configured": bool(ps.get("deposit_addresses_configured")) and bool(trc) and bool(bep),
    }


def serialize_deposit(d: dict) -> dict:
    return {
        "id": d["id"],
        "network": d["network"],
        "amount": fmt(d["amount"]),
        "approved_amount": fmt(d["approved_amount"]) if d.get("approved_amount") is not None else None,
        "status": d["status"],
        "tx_hash": d.get("tx_hash"),
        "admin_note": d.get("admin_note"),
        "created_at": d.get("created_at"),
        "decided_at": d.get("decided_at"),
    }


async def create_deposit(user_id: str, network: str, amount, tx_hash: str) -> dict:
    if network not in NETWORKS:
        raise HTTPException(status_code=422, detail={"code": "invalid_network", "message": "Unsupported network."})

    try:
        amt = to_dec(amount)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(status_code=422, detail={"code": "invalid_amount", "message": "Invalid amount."})
    if amt < MIN_DEPOSIT:
        raise HTTPException(status_code=400, detail={
            "code": "below_minimum",
            "message": f"Minimum deposit is {fmt(MIN_DEPOSIT)} USDT.",
            "min_deposit": fmt(MIN_DEPOSIT),
        })

    txh = _norm_hash(tx_hash)
    if len(txh) < 8:
        raise HTTPException(status_code=422, detail={"code": "invalid_tx_hash", "message": "Enter a valid transaction hash."})

    # Reject duplicate on-chain tx hashes (globally, any network / any status).
    existing = await db.deposits.find_one({"tx_hash": txh})
    if existing:
        raise HTTPException(status_code=409, detail={
            "code": "duplicate_tx_hash",
            "message": "This transaction hash has already been submitted.",
        })

    ts = _now()
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "network": network,
        "amount": d128(amt),
        "status": "pending",
        "tx_hash": txh,
        "approved_amount": None,
        "admin_id": None,
        "admin_note": None,
        "created_at": ts,
        "updated_at": ts,
    }
    try:
        await db.deposits.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail={
            "code": "duplicate_tx_hash",
            "message": "This transaction hash has already been submitted.",
        })
    await notify_service.create(
        user_id, ntype="deposit_submitted",
        title="Deposit submitted",
        body=f"Your {network} deposit of {fmt(doc['amount'])} USDT was submitted and is pending admin approval.",
        dedupe_key=f"deposit-submitted:{doc['id']}",
    )
    return serialize_deposit(doc)


async def list_user(user_id: str, limit: int = 50):
    cur = db.deposits.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [serialize_deposit(d) async for d in cur]


async def admin_list(status: str | None = None, limit: int = 200):
    q = {}
    if status:
        q["status"] = status
    cur = db.deposits.find(q).sort("created_at", -1).limit(limit)
    deposits = [d async for d in cur]
    # Attach basic user info.
    user_ids = list({d["user_id"] for d in deposits})
    users = {}
    if user_ids:
        async for u in db.users.find({"id": {"$in": user_ids}}, {"id": 1, "name": 1, "email": 1}):
            users[u["id"]] = {"name": u.get("name"), "email": u.get("email")}
    out = []
    for d in deposits:
        row = serialize_deposit(d)
        row["user"] = users.get(d["user_id"], {"name": None, "email": None})
        row["user_id"] = d["user_id"]
        out.append(row)
    return out


async def approve(deposit_id: str, admin_id: str, approved_amount=None, note: str | None = None) -> dict:
    dep = await db.deposits.find_one({"id": deposit_id})
    if not dep:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Deposit not found."})
    if dep["status"] == "rejected":
        raise HTTPException(status_code=409, detail={"code": "already_rejected", "message": "Deposit was already rejected."})

    # Amount to credit: admin may adjust; default = submitted amount.
    if approved_amount is None or str(approved_amount) == "":
        credit_amt = to_dec(dep["amount"])
    else:
        try:
            credit_amt = to_dec(approved_amount)
        except (InvalidOperation, ValueError, TypeError):
            raise HTTPException(status_code=422, detail={"code": "invalid_amount", "message": "Invalid approved amount."})
    if credit_amt <= 0:
        raise HTTPException(status_code=422, detail={"code": "invalid_amount", "message": "Approved amount must be positive."})

    # Atomic claim pending->approved (idempotent: a second approve is a no-op flip).
    ts = _now()
    await db.deposits.update_one(
        {"id": deposit_id, "status": "pending"},
        {"$set": {
            "status": "approved", "approved_amount": d128(credit_amt),
            "admin_id": admin_id, "admin_note": note, "decided_at": ts, "updated_at": ts,
        }},
    )
    # Re-read; if it was already approved earlier, heal by using its recorded approved_amount.
    dep = await db.deposits.find_one({"id": deposit_id})
    final_amt = to_dec(dep.get("approved_amount") if dep.get("approved_amount") is not None else credit_amt)

    # Credit the wallet (idempotent by key -> exact approved amount credited once).
    await wallet_service.credit(
        dep["user_id"], final_amt, tx_type="DEPOSIT",
        ref_type="deposit", ref_id=deposit_id,
        idempotency_key=f"deposit-approve:{deposit_id}",
        note=f"{dep['network']} USDT deposit approved",
    )
    await notify_service.create(
        dep["user_id"], ntype="deposit_approved",
        title="Deposit approved",
        body=f"Your {dep['network']} deposit of {fmt(final_amt)} USDT was approved and credited to your wallet.",
        dedupe_key=f"deposit-approved:{deposit_id}",
    )
    return serialize_deposit(dep)


async def reject(deposit_id: str, admin_id: str, note: str | None = None) -> dict:
    dep = await db.deposits.find_one({"id": deposit_id})
    if not dep:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Deposit not found."})
    if dep["status"] == "approved":
        raise HTTPException(status_code=409, detail={"code": "already_approved", "message": "Deposit was already approved."})

    ts = _now()
    res = await db.deposits.update_one(
        {"id": deposit_id, "status": "pending"},
        {"$set": {"status": "rejected", "admin_id": admin_id, "admin_note": note, "decided_at": ts, "updated_at": ts}},
    )
    dep = await db.deposits.find_one({"id": deposit_id})
    if res.modified_count == 1:
        await notify_service.create(
            dep["user_id"], ntype="deposit_rejected",
            title="Deposit rejected",
            body=(f"Your {dep['network']} deposit of {fmt(dep['amount'])} USDT was rejected."
                  + (f" Reason: {note}" if note else "")),
            dedupe_key=f"deposit-rejected:{deposit_id}",
        )
    return serialize_deposit(dep)


async def set_deposit_addresses(trc20: str, bep20: str, admin_id: str) -> dict:
    trc20 = (trc20 or "").strip()
    bep20 = (bep20 or "").strip()
    if not trc20 or not bep20:
        raise HTTPException(status_code=422, detail={"code": "invalid_address", "message": "Both TRC20 and BEP20 addresses are required."})
    await db.platform_settings.update_one(
        {"id": _PLATFORM_ID},
        {"$set": {
            "deposit_addresses": {"TRC20": trc20, "BEP20": bep20},
            "deposit_addresses_configured": True,
            "updated_at": _now(), "updated_by": admin_id,
        }},
        upsert=True,
    )
    return await get_config()
