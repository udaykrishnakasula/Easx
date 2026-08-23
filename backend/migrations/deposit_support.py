"""m0005 — deposit flow support.

1. Global unique sparse index on deposits.tx_hash so the SAME on-chain transaction
   hash can never be submitted twice (across any network / status).
2. Seed clearly-marked placeholder deposit addresses (only if none configured yet)
   so the deposit UI is usable; an admin replaces them via the admin panel, which
   flips deposit_addresses_configured -> True.
"""
from pymongo.errors import OperationFailure


async def up(db):
    try:
        await db.deposits.create_index(
            [("tx_hash", 1)], unique=True, sparse=True, name="uniq_dep_txhash_global"
        )
    except OperationFailure as e:
        if getattr(e, "code", None) not in (85, 86):
            raise

    ps = await db.platform_settings.find_one({"id": "platform"})
    addrs = (ps or {}).get("deposit_addresses") or {}
    if not addrs.get("TRC20") and not addrs.get("BEP20"):
        await db.platform_settings.update_one(
            {"id": "platform"},
            {"$set": {
                "deposit_addresses": {
                    "TRC20": "TEasyXPlaceholderSetRealAddressInAdmin1",
                    "BEP20": "0xEasyXPlaceholderSetRealAddressInAdminPanel",
                },
                "deposit_addresses_configured": False,
            }},
        )
