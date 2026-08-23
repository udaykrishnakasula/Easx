"""Automatic maturity engine.

All plans mature 60 days after purchase. At/after maturity_at an ACTIVE investment
pays out principal + profit into the Available Wallet, writes immutable ledger
entries, is marked MATURED with a timestamp, and an in-app notification is created.

IDEMPOTENCY (the same investment can NEVER be paid twice):
- Wallet credits use fixed idempotency keys `maturity-principal:{id}` and
  `maturity-profit:{id}` -> wallet_service guarantees a key is applied at most once,
  even under concurrent inserts (unique index + DuplicateKeyError handling).
- The active->matured flip is a single atomic conditional update.
- The maturity notification is deduped by `matured:{id}`.
- Credits happen BEFORE the status flip, so a crash mid-way is fully resumable
  (re-running re-applies nothing already applied and completes the rest).

Reminders (in-app only, no email): 7 / 3 / 1 days before maturity, each deduped.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import notify_service
import wallet_service
from db import db
from money import fmt, to_dec

logger = logging.getLogger("maturity")

REMINDER_DAYS = [7, 3, 1]
SCHED_INTERVAL = int(os.environ.get("MATURITY_INTERVAL_SECONDS", "60"))


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _parse(dt_str):
    try:
        return datetime.fromisoformat(dt_str)
    except (TypeError, ValueError):
        return None


async def mature_investment(inv: dict) -> bool:
    """Idempotently mature ONE investment. Returns True if THIS call performed the
    active->matured transition, False if it was already matured / not active."""
    if inv.get("status") != "active":
        return False

    inv_id = inv["id"]
    user_id = inv["user_id"]
    plan_name = inv.get("plan_name", "investment")
    principal = to_dec(inv["principal"])
    profit = to_dec(inv["profit_amount"])

    # 1) Return principal (idempotent by key).
    await wallet_service.credit(
        user_id, principal, tx_type="INVESTMENT_MATURITY",
        ref_type="investment", ref_id=inv_id,
        idempotency_key=f"maturity-principal:{inv_id}",
        note=f"{plan_name} principal returned at maturity",
    )
    # 2) Pay profit (idempotent by key), track lifetime earnings.
    if profit > 0:
        await wallet_service.credit(
            user_id, profit, tx_type="PROFIT",
            ref_type="investment", ref_id=inv_id,
            idempotency_key=f"maturity-profit:{inv_id}",
            note=f"{plan_name} profit at maturity",
            inc={"total_earned": profit},
        )

    # 3) Commit: atomic active -> matured (only one winner across concurrent jobs).
    res = await db.investments.update_one(
        {"id": inv_id, "status": "active"},
        {"$set": {"status": "matured", "matured_at": _now(), "updated_at": _now()}},
    )

    # 4) In-app notification (deduped -> created at most once regardless of races).
    total = principal + profit
    await notify_service.create(
        user_id,
        ntype="investment_matured",
        title="Investment matured",
        body=(
            f"Your {plan_name} matured. {fmt(total)} USDT credited to your wallet "
            f"(principal {fmt(principal)} + profit {fmt(profit)})."
        ),
        dedupe_key=f"matured:{inv_id}",
        investment_id=inv_id,
    )
    return res.modified_count == 1


async def run_maturity_sweep() -> dict:
    """Find all ACTIVE investments whose maturity time has passed and mature each
    independently. A failure on one never blocks the others."""
    now_iso = _now()
    matured = 0
    errors = 0
    cursor = db.investments.find({"status": "active", "maturity_at": {"$lte": now_iso}})
    async for inv in cursor:
        try:
            if await mature_investment(inv):
                matured += 1
        except Exception:  # noqa: BLE001 - isolate per-investment failures
            errors += 1
            logger.exception("Maturity failed for investment %s", inv.get("id"))
    if matured or errors:
        logger.info("Maturity sweep: matured=%s errors=%s", matured, errors)
    return {"matured": matured, "errors": errors, "ran_at": now_iso}


async def run_reminder_sweep() -> dict:
    """Create 7/3/1-day pre-maturity in-app reminders (deduped, idempotent)."""
    created = 0
    now = _now_dt()
    async for inv in db.investments.find({"status": "active"}):
        m = _parse(inv.get("maturity_at"))
        if not m:
            continue
        days_left = (m - now).total_seconds() / 86400.0
        for d in REMINDER_DAYS:
            # Fire once when remaining time is within (d-1, d] days.
            if d - 1 < days_left <= d:
                label = f"{d} day" + ("s" if d > 1 else "")
                ok = await notify_service.create(
                    inv["user_id"],
                    ntype="maturity_reminder",
                    title=f"Investment matures in {label}",
                    body=(
                        f"Your {inv.get('plan_name', 'investment')} matures in {label}. "
                        f"Expected payout {fmt(inv.get('maturity_amount', 0))} USDT."
                    ),
                    dedupe_key=f"reminder-{d}:{inv['id']}",
                    investment_id=inv["id"],
                )
                if ok:
                    created += 1
    return {"reminders_created": created}


async def scheduler_loop():
    """Background loop: runs the maturity + reminder sweeps on an interval.
    Robust to individual tick failures; stops cleanly on cancellation."""
    logger.info("Maturity scheduler started (interval=%ss).", SCHED_INTERVAL)
    while True:
        try:
            await run_maturity_sweep()
            await run_reminder_sweep()
        except asyncio.CancelledError:
            logger.info("Maturity scheduler stopped.")
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Maturity scheduler tick failed.")
        try:
            await asyncio.sleep(SCHED_INTERVAL)
        except asyncio.CancelledError:
            logger.info("Maturity scheduler stopped.")
            raise
