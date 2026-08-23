"""m0004 — maturity engine support.

Adds a unique sparse index on notifications.dedupe_key so that maturity payout
and 7/3/1-day reminder notifications are created at most once (idempotent under
worker retry / server restart / concurrent jobs).
"""
from pymongo.errors import OperationFailure


async def up(db):
    try:
        await db.notifications.create_index(
            [("dedupe_key", 1)], unique=True, sparse=True, name="uniq_notif_dedupe"
        )
    except OperationFailure as e:
        # 85/86: an equivalent index already exists.
        if getattr(e, "code", None) not in (85, 86):
            raise
