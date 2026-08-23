"""USDT withdrawal service (manual processing).

Flow:
  1. User (KYC-approved) requests a withdrawal to a destination address. The amount
     is DEBITED (held) from their available wallet immediately so it cannot be
     double-spent while pending.
  2. Admin APPROVES (money stays held) or REJECTS (held amount is refunded).
  3. Admin PROCESSES an approved withdrawal: records the on-chain TX hash and marks
     it PAID (money has left the platform).

Wallet integrity: the request debit and the reject refund are both idempotent
ledger entries, so balances always reconcile.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException

import notify_service
import wallet_service
from db import db
from money import d128, fmt, to_dec

MIN_WITHDRAWAL = Decimal("10")
NETWORKS = ["TRC20", "BEP20"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_config() -> dict:
    return {
        "currency": "USDT",
        "min_withdrawal": fmt(MIN_WITHDRAWAL),
        "networks": NETWORKS,
    }


def serialize(w: dict) -> dict:
    return {
        "id": w["id"],
        "network": w["network"],
        "amount": fmt(w["amount"]),
        "to_address": w.get("to_address"),
        "status": w["status"],
        "tx_hash": w.get("tx_hash"),
        "admin_note": w.get("admin_note"),
        "created_at": w.get("created_at"),
        "decided_at": w.get("decided_at"),
        "paid_at": w.get("paid_at"),
    }


async def create(user: dict, network: str, amount, to_address: str) -> dict:
    if user.get("kyc_status") != "approved":
        raise HTTPException(status_code=403, detail={
            "code": "kyc_required",
            "message": "Complete KYC verification to unlock withdrawals.",
        })
    if network not in NETWORKS:
        raise HTTPException(status_code=422, detail={"code": "invalid_network", "message": "Unsupported network."})
    addr = (to_address or "").strip()
    if len(addr) < 8:
        raise HTTPException(status_code=422, detail={"code": "invalid_address", "message": "Enter a valid destination address."})
    try:
        amt = to_dec(amount)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(status_code=422, detail={"code": "invalid_amount", "message": "Invalid amount."})
    if amt < MIN_WITHDRAWAL:
        raise HTTPException(status_code=400, detail={
            "code": "below_minimum",
            "message": f"Minimum withdrawal is {fmt(MIN_WITHDRAWAL)} USDT.",
            "min_withdrawal": fmt(MIN_WITHDRAWAL),
        })

    wid = str(uuid.uuid4())
    ts = _now()
    doc = {
        "id": wid, "user_id": user["id"], "network": network,
        "amount": d128(amt), "to_address": addr, "status": "pending",
        "tx_hash": None, "admin_id": None, "admin_note": None,
        "idempotency_key": f"withdraw:{wid}",
        "created_at": ts, "updated_at": ts,
    }
    await db.withdrawals.insert_one(doc)

    # Hold the funds now (debit). Roll back the request on insufficient balance.
    try:
        await wallet_service.debit(
            user["id"], amt, tx_type="WITHDRAWAL",
            ref_type="withdrawal", ref_id=wid,
            idempotency_key=f"withdraw:{wid}",
            note=f"{network} withdrawal request",
        )
    except wallet_service.InsufficientBalance:
        await db.withdrawals.delete_one({"id": wid})
        raise

    await notify_service.create(
        user["id"], ntype="withdrawal_submitted",
        title="Withdrawal submitted",
        body=f"Your {network} withdrawal request of {fmt(amt)} USDT was submitted and is pending admin approval.",
        dedupe_key=f"withdrawal-submitted:{wid}",
    )
    return serialize(doc)


async def list_user(user_id: str, limit: int = 50) -> list:
    cur = db.withdrawals.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [serialize(w) async for w in cur]


async def admin_list(status: str | None = None, limit: int = 200) -> list:
    q = {}
    if status:
        q["status"] = status
    withdrawals = [w async for w in db.withdrawals.find(q).sort("created_at", -1).limit(limit)]
    user_ids = list({w["user_id"] for w in withdrawals})
    users = {}
    if user_ids:
        async for u in db.users.find({"id": {"$in": user_ids}}, {"id": 1, "name": 1, "email": 1}):
            users[u["id"]] = {"name": u.get("name"), "email": u.get("email")}
    out = []
    for w in withdrawals:
        row = serialize(w)
        row["user"] = users.get(w["user_id"], {"name": None, "email": None})
        row["user_id"] = w["user_id"]
        out.append(row)
    return out


async def _get(wid: str) -> dict:
    w = await db.withdrawals.find_one({"id": wid})
    if not w:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Withdrawal not found."})
    return w


async def approve(wid: str, admin_id: str, note: str | None = None) -> dict:
    w = await _get(wid)
    if w["status"] != "pending":
        raise HTTPException(status_code=409, detail={"code": "invalid_state", "message": f"Cannot approve a {w['status']} withdrawal."})
    ts = _now()
    await db.withdrawals.update_one(
        {"id": wid, "status": "pending"},
        {"$set": {"status": "approved", "admin_id": admin_id, "admin_note": note, "decided_at": ts, "updated_at": ts}},
    )
    w = await _get(wid)
    await notify_service.create(
        w["user_id"], ntype="withdrawal_approved", title="Withdrawal approved",
        body=f"Your {w['network']} withdrawal of {fmt(w['amount'])} USDT was approved and is being processed.",
        dedupe_key=f"withdrawal-approved:{wid}",
    )
    return serialize(w)


async def reject(wid: str, admin_id: str, note: str | None = None) -> dict:
    w = await _get(wid)
    if w["status"] not in ("pending", "approved"):
        raise HTTPException(status_code=409, detail={"code": "invalid_state", "message": f"Cannot reject a {w['status']} withdrawal."})
    ts = _now()
    res = await db.withdrawals.update_one(
        {"id": wid, "status": {"$in": ["pending", "approved"]}},
        {"$set": {"status": "rejected", "admin_id": admin_id, "admin_note": note, "decided_at": ts, "updated_at": ts}},
    )
    # Refund the held amount (idempotent). Only the winning flip triggers work,
    # but the credit key guarantees a single refund even on retries.
    await wallet_service.credit(
        w["user_id"], to_dec(w["amount"]), tx_type="WITHDRAWAL_REVERSAL",
        ref_type="withdrawal", ref_id=wid,
        idempotency_key=f"withdraw-reverse:{wid}",
        note=f"{w['network']} withdrawal rejected \u2014 amount returned",
    )
    w = await _get(wid)
    if res.modified_count == 1:
        await notify_service.create(
            w["user_id"], ntype="withdrawal_rejected", title="Withdrawal rejected",
            body=(f"Your {w['network']} withdrawal of {fmt(w['amount'])} USDT was rejected and the amount was returned to your wallet."
                  + (f" Reason: {note}" if note else "")),
            dedupe_key=f"withdrawal-rejected:{wid}",
        )
    return serialize(w)


async def process(wid: str, admin_id: str, tx_hash: str) -> dict:
    w = await _get(wid)
    if w["status"] != "approved":
        raise HTTPException(status_code=409, detail={"code": "invalid_state", "message": "Only approved withdrawals can be processed."})
    txh = (tx_hash or "").strip()
    if len(txh) < 8:
        raise HTTPException(status_code=422, detail={"code": "invalid_tx_hash", "message": "Enter a valid blockchain transaction hash."})
    ts = _now()
    await db.withdrawals.update_one(
        {"id": wid, "status": "approved"},
        {"$set": {"status": "paid", "tx_hash": txh, "admin_id": admin_id, "paid_at": ts, "updated_at": ts}},
    )
    w = await _get(wid)
    await notify_service.create(
        w["user_id"], ntype="withdrawal_paid", title="Withdrawal paid",
        body=f"Your {w['network']} withdrawal of {fmt(w['amount'])} USDT has been sent. TX: {txh}",
        dedupe_key=f"withdrawal-paid:{wid}",
    )
    return serialize(w)
