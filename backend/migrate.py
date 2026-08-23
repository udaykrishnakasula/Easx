"""Standalone migration CLI + schema integrity verification.

Usage:
    python migrate.py          # run pending migrations
    python migrate.py --verify # run + print schema integrity report
"""
import asyncio
import sys

from db import db
from migrations.runner import MIGRATIONS, run_migrations

EXPECTED_COLLECTIONS = [
    "users", "user_profiles", "email_verifications", "password_resets",
    "investment_plans", "investments", "wallets", "wallet_transactions",
    "deposits", "withdrawals", "withdrawal_addresses", "referrals",
    "referral_commissions", "kyc_records", "kyc_documents", "notifications",
    "admin", "audit_logs", "platform_settings", "maintenance_settings",
    "schema_migrations",
]


async def verify():
    print("\n=== SCHEMA INTEGRITY REPORT ===")
    cols = await db.list_collection_names()
    missing = [c for c in EXPECTED_COLLECTIONS if c not in cols]
    print(f"Collections present: {len(cols)} | Expected: {len(EXPECTED_COLLECTIONS)}")
    if missing:
        print(f"!! MISSING COLLECTIONS: {missing}")
    else:
        print("All expected collections present. OK")

    print("\n-- Applied migrations --")
    async for doc in db.schema_migrations.find({}, {"_id": 0}).sort("version", 1):
        print(f"  v{doc['version']} {doc['name']} @ {doc.get('applied_at')}")
    print(f"  (defined: {[m[0] for m in MIGRATIONS]})")

    print("\n-- Investment plans (exact-decimal) --")
    async for p in db.investment_plans.find({}, {"_id": 0}).sort("display_order", 1):
        print(f"  #{p['display_order']} {p['name']:<9} price={p['price']} "
              f"lock={p['lock_days']}d profit={p['profit_percentage']}% "
              f"maturity={p['maturity_percentage']}% active={p['is_active']} "
              f"types(price={type(p['price']).__name__})")
    print(f"  plan count: {await db.investment_plans.count_documents({})} (expected 4)")

    print("\n-- Singletons --")
    ps = await db.platform_settings.find_one({"id": "platform"}, {"_id": 0})
    ms = await db.maintenance_settings.find_one({"id": "maintenance"}, {"_id": 0})
    print(f"  platform_settings: currency={ps and ps.get('currency')} "
          f"referral%={ps and ps.get('referral_percentage')}")
    print(f"  maintenance_settings: is_enabled={ms and ms.get('is_enabled')}")
    print(f"  admin records: {await db.admin.count_documents({})}")
    print(f"  wallets: {await db.wallets.count_documents({})} | "
          f"users: {await db.users.count_documents({})}")

    print("\n-- Index counts per collection --")
    for c in EXPECTED_COLLECTIONS:
        if c in cols:
            info = await db[c].index_information()
            print(f"  {c:<22} indexes={len(info)}: {list(info.keys())}")
    print("\n=== END REPORT ===\n")


async def main():
    newly = await run_migrations(db)
    print(f"Migrations run. Newly applied: {newly}")
    if "--verify" in sys.argv:
        await verify()


if __name__ == "__main__":
    asyncio.run(main())
