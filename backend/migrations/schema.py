"""m0001 — initial normalized schema: collections, $jsonSchema validators, indexes.

Money fields use bsonType 'decimal' (Decimal128). Status fields use enum
constraints. Foreign keys are referenced UUID string fields (enforced at the
application layer; indexed here for integrity/perf).
"""
from .helpers import ensure_collection, ensure_indexes, schema

S = {"bsonType": "string"}
BOOL = {"bsonType": "bool"}
INT = {"bsonType": "int"}
DEC = {"bsonType": "decimal"}
S_NULL = {"bsonType": ["string", "null"]}


def _enum(values, nullable=False):
    types = ["string", "null"] if nullable else "string"
    return {"bsonType": types, "enum": values + ([None] if nullable else [])}


# name -> (validator, indexes)
COLLECTIONS = {
    "users": (
        schema(
            ["id", "email", "phone", "password_hash", "role", "status"],
            {
                "id": S, "email": S, "phone": S, "password_hash": S,
                "role": _enum(["user", "admin"]),
                "status": _enum(["active", "banned", "suspended"]),
                "kyc_status": _enum(["none", "pending", "approved", "rejected"]),
                "email_verified": BOOL,
                "referral_code": S, "referred_by": S_NULL,
            },
        ),
        [
            {"keys": [("email", 1)], "unique": True, "name": "uniq_email"},
            {"keys": [("phone", 1)], "unique": True, "name": "uniq_phone"},
            {"keys": [("referral_code", 1)], "unique": True, "name": "uniq_referral_code"},
            {"keys": [("referred_by", 1)], "name": "idx_referred_by"},
        ],
    ),
    "user_profiles": (
        schema(["user_id"], {"user_id": S, "full_name": S_NULL}),
        [{"keys": [("user_id", 1)], "unique": True, "name": "uniq_profile_user"}],
    ),
    "email_verifications": (
        schema(["user_id", "token_hash", "expires_at"],
               {"user_id": S, "token_hash": S, "expires_at": S}),
        [
            {"keys": [("token_hash", 1)], "unique": True, "name": "uniq_email_token"},
            {"keys": [("user_id", 1)], "name": "idx_ev_user"},
        ],
    ),
    "password_resets": (
        schema(["user_id", "token_hash", "expires_at"],
               {"user_id": S, "token_hash": S, "expires_at": S}),
        [
            {"keys": [("token_hash", 1)], "unique": True, "name": "uniq_reset_token"},
            {"keys": [("user_id", 1)], "name": "idx_pr_user"},
        ],
    ),
    "investment_plans": (
        schema(
            ["id", "key", "name", "price", "lock_days", "profit_percentage",
             "maturity_percentage", "display_order", "is_active"],
            {
                "id": S,
                "key": _enum(["silver", "gold", "platinum", "diamond"]),
                "name": S, "price": DEC, "lock_days": INT,
                "profit_percentage": DEC, "maturity_percentage": DEC,
                "display_order": INT, "is_active": BOOL,
            },
        ),
        [
            {"keys": [("key", 1)], "unique": True, "name": "uniq_plan_key"},
            {"keys": [("display_order", 1)], "unique": True, "name": "uniq_plan_order"},
        ],
    ),
    "investments": (
        schema(
            ["id", "user_id", "plan_id", "plan_key", "status", "principal",
             "profit_amount", "maturity_amount", "source"],
            {
                "id": S, "user_id": S, "plan_id": S,
                "plan_key": _enum(["silver", "gold", "platinum", "diamond"]),
                "status": _enum(["pending", "active", "matured", "cancelled"]),
                "source": _enum(["wallet", "deposit"]),
                "principal": DEC, "profit_amount": DEC, "maturity_amount": DEC,
                # snapshot of plan terms at purchase time
                "profit_percentage_snapshot": DEC,
                "maturity_percentage_snapshot": DEC,
                "lock_days_snapshot": INT,
                "referral_paid": BOOL,
                "idempotency_key": S_NULL,
            },
        ),
        [
            {"keys": [("user_id", 1), ("created_at", -1)], "name": "idx_inv_user"},
            {"keys": [("status", 1), ("maturity_at", 1)], "name": "idx_inv_status_maturity"},
            {"keys": [("plan_id", 1)], "name": "idx_inv_plan"},
            {"keys": [("idempotency_key", 1)], "unique": True, "sparse": True,
             "name": "uniq_inv_idem"},
        ],
    ),
    "wallets": (
        schema(
            ["id", "user_id", "available_balance", "currency"],
            {
                "id": S, "user_id": S, "currency": S,
                "available_balance": DEC, "total_invested": DEC,
                "total_earned": DEC, "version": INT,
            },
        ),
        [{"keys": [("user_id", 1)], "unique": True, "name": "uniq_wallet_user"}],
    ),
    "wallet_transactions": (
        schema(
            ["id", "wallet_id", "user_id", "type", "direction", "amount", "balance_after"],
            {
                "id": S, "wallet_id": S, "user_id": S,
                "type": _enum([
                    "DEPOSIT", "INVESTMENT", "INVESTMENT_MATURITY", "PROFIT",
                    "REFERRAL_COMMISSION", "WITHDRAWAL", "WITHDRAWAL_REVERSAL",
                    "REINVESTMENT", "ADMIN_ADJUSTMENT", "REFUND",
                ]),
                "direction": _enum(["credit", "debit"]),
                "amount": DEC, "balance_after": DEC,
                "ref_type": _enum(
                    ["deposit", "investment", "withdrawal", "referral", "admin", "system"],
                    nullable=True),
                "ref_id": S_NULL,
                "status": _enum(["completed", "pending", "reversed"]),
                "idempotency_key": S_NULL,
            },
        ),
        [
            {"keys": [("user_id", 1), ("created_at", -1)], "name": "idx_wtx_user"},
            {"keys": [("ref_type", 1), ("ref_id", 1)], "name": "idx_wtx_ref"},
            {"keys": [("idempotency_key", 1)], "unique": True, "sparse": True,
             "name": "uniq_wtx_idem"},
        ],
    ),
    "deposits": (
        schema(
            ["id", "user_id", "network", "amount", "status"],
            {
                "id": S, "user_id": S,
                "network": _enum(["TRC20", "BEP20"]),
                "amount": DEC,
                "status": _enum(["pending", "approved", "rejected"]),
                "tx_hash": S_NULL, "admin_id": S_NULL, "idempotency_key": S_NULL,
            },
        ),
        [
            {"keys": [("user_id", 1), ("created_at", -1)], "name": "idx_dep_user"},
            {"keys": [("status", 1), ("created_at", -1)], "name": "idx_dep_status"},
            {"keys": [("network", 1), ("tx_hash", 1)], "unique": True, "sparse": True,
             "name": "uniq_dep_txhash"},
            {"keys": [("idempotency_key", 1)], "unique": True, "sparse": True,
             "name": "uniq_dep_idem"},
        ],
    ),
    "withdrawals": (
        schema(
            ["id", "user_id", "amount", "network", "status"],
            {
                "id": S, "user_id": S, "amount": DEC,
                "network": _enum(["TRC20", "BEP20"]),
                "status": _enum(["pending", "approved", "rejected", "paid"]),
                "address_id": S_NULL, "admin_id": S_NULL,
                "tx_hash": S_NULL, "idempotency_key": S_NULL,
            },
        ),
        [
            {"keys": [("user_id", 1), ("created_at", -1)], "name": "idx_wd_user"},
            {"keys": [("status", 1), ("created_at", -1)], "name": "idx_wd_status"},
            {"keys": [("idempotency_key", 1)], "unique": True, "sparse": True,
             "name": "uniq_wd_idem"},
        ],
    ),
    "withdrawal_addresses": (
        schema(
            ["id", "user_id", "network", "address"],
            {
                "id": S, "user_id": S,
                "network": _enum(["TRC20", "BEP20"]),
                "address": S, "label": S_NULL, "is_default": BOOL,
            },
        ),
        [
            {"keys": [("user_id", 1), ("network", 1), ("address", 1)], "unique": True,
             "name": "uniq_wd_addr"},
            {"keys": [("user_id", 1)], "name": "idx_wd_addr_user"},
        ],
    ),
    "referrals": (
        schema(
            ["id", "referrer_id", "referee_id"],
            {"id": S, "referrer_id": S, "referee_id": S, "level": INT},
        ),
        [
            {"keys": [("referee_id", 1)], "unique": True, "name": "uniq_referee"},
            {"keys": [("referrer_id", 1)], "name": "idx_referrer"},
        ],
    ),
    "referral_commissions": (
        schema(
            ["id", "referrer_id", "referee_id", "amount", "status"],
            {
                "id": S, "referrer_id": S, "referee_id": S,
                "amount": DEC, "percentage": DEC,
                "status": _enum(["pending", "paid"]),
                "investment_id": S_NULL, "wallet_transaction_id": S_NULL,
            },
        ),
        [
            {"keys": [("referee_id", 1)], "unique": True, "name": "uniq_commission_referee"},
            {"keys": [("investment_id", 1)], "unique": True, "sparse": True,
             "name": "uniq_commission_investment"},
            {"keys": [("referrer_id", 1)], "name": "idx_commission_referrer"},
        ],
    ),
    "kyc_records": (
        schema(
            ["id", "user_id", "status"],
            {
                "id": S, "user_id": S,
                "status": _enum(["none", "pending", "approved", "rejected"]),
                "id_type": _enum(["aadhaar", "national_id", "passport", "other"], nullable=True),
                "id_number_encrypted": S_NULL, "admin_id": S_NULL,
            },
        ),
        [
            {"keys": [("user_id", 1)], "unique": True, "name": "uniq_kyc_user"},
            {"keys": [("status", 1)], "name": "idx_kyc_status"},
        ],
    ),
    "kyc_documents": (
        schema(
            ["id", "user_id", "doc_type"],
            {
                "id": S, "user_id": S, "kyc_record_id": S_NULL,
                "doc_type": _enum(["id_front", "id_back", "selfie"]),
                "file_path": S_NULL, "mime": S_NULL,
            },
        ),
        [
            {"keys": [("kyc_record_id", 1)], "name": "idx_kycdoc_record"},
            {"keys": [("user_id", 1)], "name": "idx_kycdoc_user"},
        ],
    ),
    "notifications": (
        schema(
            ["id", "channel"],
            {
                "id": S, "user_id": S_NULL,
                "channel": _enum(["in_app", "email"]),
                "is_read": BOOL, "type": S_NULL, "title": S_NULL,
            },
        ),
        [
            {"keys": [("user_id", 1), ("is_read", 1), ("created_at", -1)], "name": "idx_notif_user"},
            {"keys": [("created_at", -1)], "name": "idx_notif_created"},
        ],
    ),
    "admin": (
        schema(
            ["id", "user_id"],
            {"id": S, "user_id": S, "is_super": BOOL, "permissions": {"bsonType": "array"}},
        ),
        [{"keys": [("user_id", 1)], "unique": True, "name": "uniq_admin_user"}],
    ),
    "audit_logs": (
        schema(
            ["id", "action"],
            {
                "id": S, "action": S,
                "actor_id": S_NULL, "actor_role": S_NULL,
                "entity_type": S_NULL, "entity_id": S_NULL,
            },
        ),
        [
            {"keys": [("entity_type", 1), ("entity_id", 1)], "name": "idx_audit_entity"},
            {"keys": [("actor_id", 1), ("created_at", -1)], "name": "idx_audit_actor"},
            {"keys": [("created_at", -1)], "name": "idx_audit_created"},
        ],
    ),
    "platform_settings": (
        schema(["id"], {"id": S, "referral_percentage": DEC, "currency": S}),
        [{"keys": [("id", 1)], "unique": True, "name": "uniq_platform_id"}],
    ),
    "maintenance_settings": (
        schema(["id", "is_enabled"], {"id": S, "is_enabled": BOOL, "message": S_NULL}),
        [{"keys": [("id", 1)], "unique": True, "name": "uniq_maintenance_id"}],
    ),
}

# TTL indexes (auto-expire tokens once past expires_at). Added separately because
# expires_at is stored as ISO string in app code; TTL requires a BSON date, so we
# additionally index a numeric expiry. We keep a plain index here; TTL enforcement
# is handled by a cleanup job in a later phase.


async def up(db):
    for name, (validator, indexes) in COLLECTIONS.items():
        await ensure_collection(db, name, validator)
        await ensure_indexes(db, name, indexes)
