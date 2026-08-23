"""Direct (single-level) referral commission engine.

Rules (per spec):
- ONLY the direct referrer earns. No multi-level.
- Commission = referral_percentage (default 10%) of each successfully-approved
  investment's principal.
- ONE commission record PER successful investment (buying 3 cards => 3 records).
- Self-referral prohibited; a referee has at most one referrer (set once at
  signup, immutable) => duplicate relationships impossible.
- Cancelled/rejected investment => NO commission.
- Commission is credited IMMEDIATELY to the referrer's wallet (withdrawable).
- Idempotent: never pay twice for the same investment (unique investment_id on
  referral_commissions + unique idempotency_key on the wallet ledger entry).
- If an investment is later cancelled by admin, the already-paid commission is
  NOT reversed (no reversal logic here by design).
"""
import logging
import uuid
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

import notify_service
import wallet_service
from db import db
from money import d128, fmt, to_dec

logger = logging.getLogger("referral")

DEFAULT_PERCENTAGE = to_dec(10)
SUCCESSFUL_STATUSES = ("active", "matured")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _referral_percentage() -> "Decimal":
    ps = await db.platform_settings.find_one({"id": "platform"})
    if ps and ps.get("referral_percentage") is not None:
        return to_dec(ps["referral_percentage"])
    return DEFAULT_PERCENTAGE


async def pay_for_investment(inv: dict) -> dict | None:
    """Pay the direct referrer their commission for one successful investment.

    Returns the commission doc if a NEW payout happened, else None (no referrer,
    self-referral, already paid, or not a successful investment). Never raises —
    a referral failure must never break the purchase flow.
    """
    try:
        if not inv or inv.get("status") not in SUCCESSFUL_STATUSES:
            return None

        inv_id = inv["id"]
        referee_id = inv["user_id"]

        # Fast idempotency short-circuit.
        if inv.get("referral_paid") is True:
            return None
        if await db.referral_commissions.find_one({"investment_id": inv_id}):
            return None

        referee = await db.users.find_one({"id": referee_id})
        if not referee:
            return None
        referrer_id = referee.get("referred_by")
        if not referrer_id:
            return None  # No direct referrer => no commission.
        if referrer_id == referee_id:
            return None  # Self-referral guard (defensive).

        referrer = await db.users.find_one({"id": referrer_id})
        if not referrer:
            return None

        principal = to_dec(inv["principal"])
        pct = await _referral_percentage()
        amount = (principal * pct) / to_dec(100)
        if amount <= 0:
            return None

        commission_id = str(uuid.uuid4())
        comm_doc = {
            "id": commission_id,
            "referrer_id": referrer_id,
            "referee_id": referee_id,
            "investment_id": inv_id,
            "plan_key": inv.get("plan_key"),
            "amount": d128(amount),
            "percentage": d128(pct),
            "status": "pending",
            "wallet_transaction_id": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        try:
            await db.referral_commissions.insert_one(comm_doc)
        except DuplicateKeyError:
            # Another concurrent path already created the commission for this
            # investment. Idempotent: do nothing more.
            return None

        # Credit the referrer's wallet immediately (available + withdrawable).
        tx = await wallet_service.credit(
            referrer_id, amount, tx_type="REFERRAL_COMMISSION",
            ref_type="referral", ref_id=commission_id,
            idempotency_key=f"referral:{inv_id}",
            note=f"Direct referral commission ({fmt(pct)}%) from {referee.get('name') or 'referral'}",
            inc={"total_earned": amount},
        )

        await db.referral_commissions.update_one(
            {"id": commission_id},
            {"$set": {"status": "paid", "wallet_transaction_id": tx["id"], "updated_at": _now()}},
        )
        await db.investments.update_one(
            {"id": inv_id}, {"$set": {"referral_paid": True, "updated_at": _now()}}
        )

        # Best-effort in-app notification to the referrer.
        try:
            await notify_service.create(
                user_id=referrer_id,
                ntype="referral_commission",
                title="Referral commission earned",
                body=f"You earned {fmt(amount)} USDT ({fmt(pct)}%) from a referral's {inv.get('plan_name') or inv.get('plan_key')} investment.",
                dedupe_key=f"referral_commission:{inv_id}",
                investment_id=inv_id,
            )
        except Exception:  # noqa: BLE001 - notifications must never block payout
            logger.exception("Referral notification failed for investment %s", inv_id)

        comm_doc["status"] = "paid"
        comm_doc["wallet_transaction_id"] = tx["id"]
        return comm_doc
    except Exception:  # noqa: BLE001 - referral must never break the purchase
        logger.exception("Referral commission failed for investment %s", (inv or {}).get("id"))
        return None


def serialize_commission(c: dict) -> dict:
    return {
        "id": c["id"],
        "referee_id": c.get("referee_id"),
        "referee_name": c.get("referee_name"),
        "investment_id": c.get("investment_id"),
        "plan_key": c.get("plan_key"),
        "amount": fmt(c.get("amount", 0)),
        "percentage": fmt(c.get("percentage", 0)),
        "status": c.get("status"),
        "created_at": c.get("created_at"),
    }


async def summary(user: dict) -> dict:
    """Referral dashboard payload for the authenticated user."""
    user_id = user["id"]
    referral_code = user.get("referral_code")

    # Direct referees (level 1).
    referees = [r async for r in db.users.find(
        {"referred_by": user_id}, {"id": 1, "name": 1, "created_at": 1}
    )]
    referee_names = {r["id"]: r.get("name") for r in referees}

    # Commissions this user has EARNED (as referrer).
    commissions = [c async for c in db.referral_commissions.find(
        {"referrer_id": user_id}
    ).sort("created_at", -1)]

    total_earned = to_dec(0)
    for c in commissions:
        if c.get("status") == "paid":
            total_earned += to_dec(c.get("amount", 0))
        c["referee_name"] = referee_names.get(c.get("referee_id"))

    pct = await _referral_percentage()
    return {
        "referral_code": referral_code,
        "referral_percentage": fmt(pct),
        "total_referrals": len(referees),
        "total_commission_earned": fmt(total_earned),
        "total_commissions": len(commissions),
        "referrals": [
            {"id": r["id"], "name": r.get("name"), "joined_at": r.get("created_at")}
            for r in sorted(referees, key=lambda x: x.get("created_at") or "", reverse=True)
        ],
        "commissions": [serialize_commission(c) for c in commissions],
    }


async def admin_overview() -> dict:
    """Platform-wide referral view for admins: every direct relationship and
    every commission paid, plus roll-up stats."""
    # Relationships are authoritative from users.referred_by (set once at signup).
    referred = [u async for u in db.users.find(
        {"referred_by": {"$ne": None}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "referred_by": 1, "created_at": 1},
    )]

    commissions = [c async for c in db.referral_commissions.find().sort("created_at", -1)]

    # Batch-load every user referenced so we can attach names/emails.
    ids = set()
    for u in referred:
        ids.add(u["id"]); ids.add(u["referred_by"])
    for c in commissions:
        ids.add(c.get("referrer_id")); ids.add(c.get("referee_id"))
    ids.discard(None)
    umap = {}
    async for u in db.users.find({"id": {"$in": list(ids)}}, {"_id": 0, "id": 1, "name": 1, "email": 1}):
        umap[u["id"]] = {"name": u.get("name"), "email": u.get("email")}

    def who(uid):
        u = umap.get(uid) or {}
        return {"id": uid, "name": u.get("name"), "email": u.get("email")}

    total_paid = to_dec(0)
    paid_count = 0
    for c in commissions:
        if c.get("status") == "paid":
            total_paid += to_dec(c.get("amount", 0))
            paid_count += 1

    relationships = [
        {"referrer": who(u["referred_by"]), "referee": who(u["id"]), "joined_at": u.get("created_at")}
        for u in sorted(referred, key=lambda x: x.get("created_at") or "", reverse=True)
    ]

    commissions_out = [
        {
            "id": c["id"],
            "referrer": who(c.get("referrer_id")),
            "referee": who(c.get("referee_id")),
            "investment_id": c.get("investment_id"),
            "plan_key": c.get("plan_key"),
            "amount": fmt(c.get("amount", 0)),
            "percentage": fmt(c.get("percentage", 0)),
            "status": c.get("status"),
            "created_at": c.get("created_at"),
        }
        for c in commissions
    ]

    return {
        "stats": {
            "total_relationships": len(referred),
            "total_referrers": len({u["referred_by"] for u in referred}),
            "total_commissions": len(commissions),
            "total_commissions_paid": paid_count,
            "total_commission_amount": fmt(total_paid),
        },
        "relationships": relationships,
        "commissions": commissions_out,
    }
