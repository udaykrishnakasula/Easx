"""m0003 — canonical ledger transaction types.

Re-applies the wallet_transactions $jsonSchema validator so the `type` field
accepts the canonical ledger categories:
DEPOSIT, INVESTMENT, INVESTMENT_MATURITY, PROFIT, REFERRAL_COMMISSION,
WITHDRAWAL, WITHDRAWAL_REVERSAL, REINVESTMENT, ADMIN_ADJUSTMENT, REFUND.
"""
from .helpers import ensure_collection
from .schema import COLLECTIONS


async def up(db):
    validator, _indexes = COLLECTIONS["wallet_transactions"]
    await ensure_collection(db, "wallet_transactions", validator)
