"""m0002 — seed investment plans, platform/maintenance settings, admin record,
and bootstrap wallet/profile rows for any existing users.

Seeds are idempotent via upsert with $setOnInsert so that re-running a migration
never overwrites values an admin may have changed later (per spec: existing plans
must not be silently reset).
"""
import uuid

from .helpers import money, now_iso

PLANS = [
    {"key": "silver", "name": "Silver", "price": 300, "lock_days": 60,
     "profit_percentage": 60, "maturity_percentage": 160, "display_order": 1},
    {"key": "gold", "name": "Gold", "price": 1000, "lock_days": 60,
     "profit_percentage": 60, "maturity_percentage": 160, "display_order": 2},
    {"key": "platinum", "name": "Platinum", "price": 5000, "lock_days": 60,
     "profit_percentage": 100, "maturity_percentage": 200, "display_order": 3},
    {"key": "diamond", "name": "Diamond", "price": 10000, "lock_days": 60,
     "profit_percentage": 100, "maturity_percentage": 200, "display_order": 4},
]


async def up(db):
    ts = now_iso()

    # --- Investment plans (exact seed, idempotent) ---
    for p in PLANS:
        await db.investment_plans.update_one(
            {"key": p["key"]},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "key": p["key"],
                "name": p["name"],
                "price": money(p["price"]),
                "lock_days": int(p["lock_days"]),
                "profit_percentage": money(p["profit_percentage"]),
                "maturity_percentage": money(p["maturity_percentage"]),
                "display_order": int(p["display_order"]),
                "is_active": True,
                "created_at": ts,
                "updated_at": ts,
            }},
            upsert=True,
        )

    # --- Platform settings (singleton) ---
    await db.platform_settings.update_one(
        {"id": "platform"},
        {"$setOnInsert": {
            "id": "platform",
            "currency": "USDT",
            "supported_networks": ["TRC20", "BEP20"],
            "deposit_addresses": {"TRC20": None, "BEP20": None},
            "referral_percentage": money(10),
            "created_at": ts,
            "updated_at": ts,
            "updated_by": None,
        }},
        upsert=True,
    )

    # --- Maintenance settings (singleton) ---
    await db.maintenance_settings.update_one(
        {"id": "maintenance"},
        {"$setOnInsert": {
            "id": "maintenance",
            "is_enabled": False,
            "allow_admin": True,
            "message": "EasyX is under scheduled maintenance. Please check back soon.",
            "created_at": ts,
            "updated_at": ts,
            "updated_by": None,
        }},
        upsert=True,
    )

    # --- Admin record linked to the seeded admin user ---
    admin_user = await db.users.find_one({"role": "admin"})
    if admin_user:
        await db.admin.update_one(
            {"user_id": admin_user["id"]},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "user_id": admin_user["id"],
                "is_super": True,
                "permissions": ["*"],
                "created_at": ts,
            }},
            upsert=True,
        )

    # --- Bootstrap wallet + profile for existing users (integrity) ---
    async for u in db.users.find({}, {"id": 1, "name": 1}):
        await db.wallets.update_one(
            {"user_id": u["id"]},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "user_id": u["id"],
                "currency": "USDT",
                "available_balance": money(0),
                "total_invested": money(0),
                "total_earned": money(0),
                "version": 0,
                "created_at": ts,
                "updated_at": ts,
            }},
            upsert=True,
        )
        await db.user_profiles.update_one(
            {"user_id": u["id"]},
            {"$setOnInsert": {
                "id": str(uuid.uuid4()),
                "user_id": u["id"],
                "full_name": u.get("name"),
                "created_at": ts,
                "updated_at": ts,
            }},
            upsert=True,
        )
