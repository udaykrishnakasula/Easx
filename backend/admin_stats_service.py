"""Admin overview / KPI aggregation (read-only)."""
from db import db
from money import fmt, to_dec


async def _sum_dec(collection, match: dict, field: str):
    total = to_dec(0)
    async for doc in collection.find(match, {field: 1}):
        if doc.get(field) is not None:
            total += to_dec(doc[field])
    return total


async def overview() -> dict:
    users_total = await db.users.count_documents({"role": {"$ne": "admin"}})
    users_active = await db.users.count_documents({"role": {"$ne": "admin"}, "status": "active"})
    users_suspended = await db.users.count_documents({"status": "suspended"})

    inv_active = await db.investments.count_documents({"status": "active"})
    inv_matured = await db.investments.count_documents({"status": "matured"})
    inv_cancelled = await db.investments.count_documents({"status": "cancelled"})
    active_principal = await _sum_dec(db.investments, {"status": "active"}, "principal")

    dep_pending = await db.deposits.count_documents({"status": "pending"})
    dep_approved_amt = await _sum_dec(db.deposits, {"status": "approved"}, "approved_amount")

    wd_pending = await db.withdrawals.count_documents({"status": "pending"})
    wd_approved = await db.withdrawals.count_documents({"status": "approved"})
    wd_paid_amt = await _sum_dec(db.withdrawals, {"status": "paid"}, "amount")

    kyc_pending = await db.kyc_records.count_documents({"status": "pending"})

    # Platform liabilities = money the platform owes users right now =
    # sum of available balances + sum of active investment principals (locked).
    available_total = await _sum_dec(db.wallets, {}, "available_balance")
    liabilities = available_total + active_principal

    commissions_paid = await _sum_dec(
        db.wallet_transactions,
        {"type": "REFERRAL_COMMISSION", "direction": "credit", "status": "completed"},
        "amount",
    )

    return {
        "users": {"total": users_total, "active": users_active, "suspended": users_suspended},
        "investments": {
            "active": inv_active, "matured": inv_matured, "cancelled": inv_cancelled,
            "active_principal": fmt(active_principal),
        },
        "deposits": {"pending": dep_pending, "approved_total": fmt(dep_approved_amt)},
        "withdrawals": {"pending": wd_pending, "approved": wd_approved, "paid_total": fmt(wd_paid_amt)},
        "kyc": {"pending": kyc_pending},
        "wallet": {
            "available_total": fmt(available_total),
            "locked_total": fmt(active_principal),
            "liabilities": fmt(liabilities),
        },
        "referrals": {"commissions_paid": fmt(commissions_paid)},
    }
