"""Investment engine. 1 card = 1 separate investment.

- Amount is FIXED to the plan price (no custom amount).
- Plan terms are SNAPSHOTTED onto the investment at purchase time so later admin
  plan edits never mutate existing investments.
- Buying debits the wallet atomically & idempotently (backend source of truth).
"""
import asyncio
import math
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

import wallet_service
import referral_service
from db import db
from money import d128, fmt, to_dec

SUCCESSFUL_STATUSES = ["active", "matured"]


def _now_dt():
    return datetime.now(timezone.utc)


def _now():
    return _now_dt().isoformat()


def _parse(dt_str):
    try:
        return datetime.fromisoformat(dt_str)
    except (TypeError, ValueError):
        return None


def remaining_days(maturity_at: str) -> int:
    m = _parse(maturity_at)
    if not m:
        return 0
    delta = m - _now_dt()
    if delta.total_seconds() <= 0:
        return 0
    return max(0, math.ceil(delta.total_seconds() / 86400))


async def get_plan(plan_key: str) -> dict:
    plan = await db.investment_plans.find_one({"key": plan_key})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return plan


def _compute_amounts(plan: dict):
    principal = to_dec(plan["price"])
    profit = principal * to_dec(plan["profit_percentage"]) / to_dec(100)
    maturity = principal * to_dec(plan["maturity_percentage"]) / to_dec(100)
    return principal, profit, maturity


def serialize_investment(inv: dict) -> dict:
    return {
        "id": inv["id"],
        "plan_key": inv["plan_key"],
        "plan_name": inv.get("plan_name"),
        "principal": fmt(inv["principal"]),
        "profit_amount": fmt(inv["profit_amount"]),
        "maturity_amount": fmt(inv["maturity_amount"]),
        "profit_percentage": fmt(inv["profit_percentage_snapshot"]) if inv.get("profit_percentage_snapshot") is not None else None,
        "maturity_percentage": fmt(inv["maturity_percentage_snapshot"]) if inv.get("maturity_percentage_snapshot") is not None else None,
        "lock_days": inv.get("lock_days_snapshot"),
        "status": inv["status"],
        "source": inv.get("source"),
        "start_at": inv.get("start_at"),
        "maturity_at": inv.get("maturity_at"),
        "matured_at": inv.get("matured_at"),
        "remaining_days": remaining_days(inv.get("maturity_at")) if inv.get("status") == "active" else 0,
        "created_at": inv.get("created_at"),
    }


async def buy_plan(user: dict, plan_key: str, idempotency_key: str | None = None) -> dict:
    user_id = user["id"]
    plan = await get_plan(plan_key)
    if not plan.get("is_active", True):
        raise HTTPException(status_code=400, detail="This plan is not currently available.")

    # Idempotent replay: return prior investment for same key.
    if idempotency_key:
        prior = await db.investments.find_one({"idempotency_key": idempotency_key, "user_id": user_id})
        if prior:
            return serialize_investment(prior)

    principal, profit, maturity = _compute_amounts(plan)

    # Early friendly insufficient-balance check.
    wallet = await wallet_service.get_or_create_wallet(user_id)
    if to_dec(wallet["available_balance"]) < principal:
        raise wallet_service.InsufficientBalance(principal, wallet["available_balance"])

    inv_id = str(uuid.uuid4())
    inv_key = idempotency_key or f"invest:{inv_id}"
    ts = _now()
    inv_doc = {
        "id": inv_id, "user_id": user_id,
        "plan_id": plan["id"], "plan_key": plan["key"], "plan_name": plan["name"],
        "status": "pending", "source": "wallet",
        "principal": d128(principal), "profit_amount": d128(profit),
        "maturity_amount": d128(maturity),
        "profit_percentage_snapshot": d128(plan["profit_percentage"]),
        "maturity_percentage_snapshot": d128(plan["maturity_percentage"]),
        "lock_days_snapshot": int(plan["lock_days"]),
        "referral_paid": False, "idempotency_key": inv_key,
        "start_at": None, "maturity_at": None, "matured_at": None,
        "created_at": ts, "updated_at": ts,
    }
    try:
        await db.investments.insert_one(inv_doc)
    except DuplicateKeyError:
        # A concurrent request with the SAME idempotency_key won the insert race.
        # Return that single investment. Retry the read briefly to tolerate the
        # tiny window before the winning insert is visible, so we never surface a
        # 500 for a duplicate/retried request (spec: idempotent, no double-spend).
        prior = None
        for _ in range(10):
            prior = await db.investments.find_one({"idempotency_key": inv_key, "user_id": user_id})
            if prior:
                break
            await asyncio.sleep(0.05)
        if prior:
            return serialize_investment(prior)
        raise HTTPException(status_code=409, detail="Duplicate request in progress, please retry.")

    # Debit wallet (atomic, idempotent). Roll back the pending investment on failure.
    try:
        await wallet_service.debit(
            user_id, principal, tx_type="INVESTMENT",
            ref_type="investment", ref_id=inv_id,
            idempotency_key=f"invest-debit:{inv_id}",
            note=f"Investment in {plan['name']} plan",
            inc={"total_invested": principal},
        )
    except wallet_service.InsufficientBalance:
        await db.investments.update_one({"id": inv_id}, {"$set": {"status": "cancelled", "updated_at": _now()}})
        raise

    start_dt = _now_dt()
    maturity_dt = start_dt + timedelta(days=int(plan["lock_days"]))
    await db.investments.update_one(
        {"id": inv_id},
        {"$set": {
            "status": "active",
            "start_at": start_dt.isoformat(),
            "maturity_at": maturity_dt.isoformat(),
            "updated_at": _now(),
        }},
    )
    inv_doc = await db.investments.find_one({"id": inv_id})

    # Direct (1-level) referral commission — paid immediately on the successful
    # investment. Best-effort & idempotent; never blocks/fails the purchase.
    await referral_service.pay_for_investment(inv_doc)

    import notify_service
    await notify_service.create(
        user["id"], ntype="investment_purchased",
        title="Investment purchased",
        body=(f"You invested in the {plan['name']} plan. It matures on "
              f"{maturity_dt.date().isoformat()} with an expected payout of "
              f"{fmt(inv_doc.get('maturity_amount', 0))} USDT."),
        dedupe_key=f"invest-purchased:{inv_id}",
        investment_id=inv_id,
    )

    return serialize_investment(inv_doc)


async def list_investments(user_id: str, plan_key: str | None = None):
    q = {"user_id": user_id, "status": {"$ne": "pending"}}
    if plan_key:
        q["plan_key"] = plan_key
    cur = db.investments.find(q).sort("created_at", -1)
    return [serialize_investment(i) async for i in cur]


async def get_investment(user_id: str, investment_id: str) -> dict:
    """Return a single investment owned by the user. 404 if not found.

    Each investment is fully independent — its own principal, dates and
    maturity are returned exactly as snapshotted at purchase time.
    """
    inv = await db.investments.find_one(
        {"id": investment_id, "user_id": user_id, "status": {"$ne": "pending"}}
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found.")
    return serialize_investment(inv)


async def admin_list_investments(status_filter: str | None = None, q: str | None = None, limit: int = 200):
    """List investments with basic user info for the admin console."""
    query: dict = {}
    if status_filter:
        query["status"] = status_filter
    else:
        query["status"] = {"$ne": "pending"}
    if q:
        rx = {"$regex": q.strip(), "$options": "i"}
        matched = [u["id"] async for u in db.users.find(
            {"$or": [{"name": rx}, {"email": rx}]}, {"id": 1}
        )]
        query["user_id"] = {"$in": matched}
    invs = [i async for i in db.investments.find(query).sort("created_at", -1).limit(limit)]
    user_ids = list({i["user_id"] for i in invs})
    users = {}
    if user_ids:
        async for u in db.users.find({"id": {"$in": user_ids}}, {"id": 1, "name": 1, "email": 1}):
            users[u["id"]] = {"name": u.get("name"), "email": u.get("email")}
    out = []
    for i in invs:
        row = serialize_investment(i)
        row["user"] = users.get(i["user_id"], {"name": None, "email": None})
        row["user_id"] = i["user_id"]
        row["refund_amount"] = fmt(i["refund_amount"]) if i.get("refund_amount") is not None else None
        row["cancel_reason"] = i.get("cancel_reason")
        row["cancelled_at"] = i.get("cancelled_at")
        out.append(row)
    return out


async def admin_cancel(investment_id: str, refund_amount, reason: str, admin_id: str) -> dict:
    """Admin-cancel an ACTIVE investment.

    - Refund amount may be $0 up to the original principal (profit is NEVER paid).
    - Already-paid referral commission is NOT reversed.
    - The active->cancelled flip is atomic so it can never race the maturity engine.
    """
    inv = await db.investments.find_one({"id": investment_id})
    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found.")
    if inv["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Only active investments can be cancelled (this one is {inv['status']}).")

    principal = to_dec(inv["principal"])
    try:
        refund = to_dec(refund_amount)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid refund amount.")
    if refund < 0 or refund > principal:
        raise HTTPException(status_code=422, detail=f"Refund must be between 0 and the principal ({fmt(principal)} USDT).")

    reason = (reason or "").strip()
    if len(reason) < 3:
        raise HTTPException(status_code=422, detail="A cancellation reason is required.")

    ts = _now()
    # Atomic claim: only the winner (vs a concurrent maturity flip) proceeds.
    res = await db.investments.update_one(
        {"id": investment_id, "status": "active"},
        {"$set": {
            "status": "cancelled", "cancelled_at": ts, "cancel_reason": reason,
            "refund_amount": d128(refund), "cancelled_by": admin_id, "updated_at": ts,
        }},
    )
    if res.modified_count != 1:
        current = await db.investments.find_one({"id": investment_id})
        raise HTTPException(status_code=409, detail=f"Investment is no longer active (now {current['status']}). No changes made.")

    # Refund to available wallet (idempotent). Profit is never included.
    if refund > 0:
        await wallet_service.credit(
            inv["user_id"], refund, tx_type="REFUND",
            ref_type="investment", ref_id=investment_id,
            idempotency_key=f"invest-cancel-refund:{investment_id}",
            note=f"Investment cancelled — {fmt(refund)} USDT refunded",
        )

    await referral_service_notify(inv, refund, reason)
    inv = await db.investments.find_one({"id": investment_id})
    return serialize_investment(inv)


async def referral_service_notify(inv: dict, refund, reason: str):
    """Notify the user their investment was cancelled (best-effort)."""
    try:
        import notify_service
        await notify_service.create(
            inv["user_id"], ntype="investment_cancelled",
            title="Investment cancelled",
            body=(f"Your {inv.get('plan_name')} investment was cancelled by an administrator. "
                  f"{fmt(refund)} USDT was refunded to your wallet. Reason: {reason}"),
            dedupe_key=f"invest-cancelled:{inv['id']}",
        )
    except Exception:
        pass


async def _plan_summary(user_id: str, plan: dict) -> dict:
    """Backend-computed lock state + aggregates for one plan."""
    invs = [i async for i in db.investments.find(
        {"user_id": user_id, "plan_key": plan["key"], "status": {"$in": SUCCESSFUL_STATUSES}}
    )]
    unlocked = len(invs) > 0
    active = [i for i in invs if i["status"] == "active"]

    total_invested = sum((to_dec(i["principal"]) for i in invs), to_dec(0))
    expected_profit = sum((to_dec(i["profit_amount"]) for i in active), to_dec(0))
    expected_maturity = sum((to_dec(i["maturity_amount"]) for i in active), to_dec(0))
    next_maturity = None
    if active:
        next_maturity = min(i["maturity_at"] for i in active if i.get("maturity_at"))

    principal, profit, maturity = _compute_amounts(plan)
    return {
        "key": plan["key"],
        "name": plan["name"],
        "display_order": plan["display_order"],
        "price": fmt(principal),
        "lock_days": int(plan["lock_days"]),
        "profit_percentage": fmt(plan["profit_percentage"]),
        "maturity_percentage": fmt(plan["maturity_percentage"]),
        "profit_amount": fmt(profit),
        "maturity_amount": fmt(maturity),
        "unlocked": unlocked,
        "cards": len(invs),
        "active_investments": len(active),
        "total_invested": fmt(total_invested),
        "expected_profit": fmt(expected_profit),
        "expected_maturity": fmt(expected_maturity),
        "next_maturity": next_maturity,
    }


async def get_plans_state(user_id: str):
    plans = [p async for p in db.investment_plans.find({}).sort("display_order", 1)]
    return [await _plan_summary(user_id, p) for p in plans]


async def get_dashboard(user: dict):
    wallet = await wallet_service.wallet_summary(user["id"])
    plans = await get_plans_state(user["id"])
    total_active = sum(p["active_investments"] for p in plans)
    total_cards = sum(p["cards"] for p in plans)
    return {
        "user": {"id": user["id"], "name": user["name"], "email": user["email"],
                 "referral_code": user.get("referral_code"), "kyc_status": user.get("kyc_status", "none")},
        "wallet": wallet,
        "plans": plans,
        "totals": {"active_investments": total_active, "total_cards": total_cards},
    }
