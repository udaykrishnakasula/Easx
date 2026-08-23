"""Versioned migration runner. Tracks applied versions in `schema_migrations`
and applies pending migrations in order. Idempotent and safe to run on startup.
"""
import logging

from . import schema as m0001_schema
from . import seed as m0002_seed
from . import ledger_types as m0003_ledger_types
from . import maturity_indexes as m0004_maturity_indexes
from . import deposit_support as m0005_deposit_support
from . import referral_commissions_fix as m0006_referral_commissions_fix
from .helpers import now_iso

logger = logging.getLogger("migrations")

# (version, name, module-with-async-up)
MIGRATIONS = [
    (1, "initial_schema", m0001_schema),
    (2, "seed_data", m0002_seed),
    (3, "canonical_ledger_types", m0003_ledger_types),
    (4, "maturity_indexes", m0004_maturity_indexes),
    (5, "deposit_support", m0005_deposit_support),
    (6, "referral_commissions_fix", m0006_referral_commissions_fix),
]


async def run_migrations(db) -> list[int]:
    applied = set()
    async for doc in db.schema_migrations.find({}, {"version": 1}):
        applied.add(doc["version"])

    newly = []
    for version, name, module in sorted(MIGRATIONS, key=lambda m: m[0]):
        if version in applied:
            continue
        logger.info("Applying migration %s: %s", version, name)
        await module.up(db)
        await db.schema_migrations.update_one(
            {"version": version},
            {"$set": {"version": version, "name": name, "applied_at": now_iso()}},
            upsert=True,
        )
        newly.append(version)
    if newly:
        logger.info("Applied migrations: %s", newly)
    else:
        logger.info("No pending migrations.")
    return newly
