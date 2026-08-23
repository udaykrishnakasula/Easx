"""m0006 — direct (1-level) referral commissions.

The original schema put a UNIQUE index on referral_commissions.referee_id, which
would (incorrectly) allow only ONE commission per referred user for their whole
lifetime. The spec requires ONE commission record PER successful investment
(e.g. a referee who buys 3 Gold cards generates 3 separate $100 commissions).

Fix:
- Drop the unique index on referee_id.
- Add a NON-unique index on referee_id (query support).
- Ensure the unique sparse index on investment_id exists — this is the real
  idempotency guard (never pay twice for the same investment).
"""
from pymongo.errors import OperationFailure


async def up(db):
    # Drop the wrong unique index on referee_id if present.
    try:
        await db.referral_commissions.drop_index("uniq_commission_referee")
    except OperationFailure as e:
        # 27 IndexNotFound: nothing to drop — fine.
        if getattr(e, "code", None) != 27:
            raise

    # Non-unique index on referee_id (list a referee's generated commissions).
    try:
        await db.referral_commissions.create_index(
            [("referee_id", 1)], name="idx_commission_referee"
        )
    except OperationFailure as e:
        if getattr(e, "code", None) not in (85, 86):
            raise

    # Idempotency guard: at most one commission per investment.
    try:
        await db.referral_commissions.create_index(
            [("investment_id", 1)], unique=True, sparse=True,
            name="uniq_commission_investment",
        )
    except OperationFailure as e:
        if getattr(e, "code", None) not in (85, 86):
            raise
