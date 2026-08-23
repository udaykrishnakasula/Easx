"""Migration helpers: Decimal128 money, timestamps, idempotent collection ops."""
from datetime import datetime, timezone
from decimal import Decimal

from bson.decimal128 import Decimal128
from pymongo.errors import OperationFailure


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def money(value) -> Decimal128:
    """Exact decimal for all monetary values. Never use float."""
    return Decimal128(Decimal(str(value)))


async def ensure_collection(db, name: str, validator: dict | None = None) -> None:
    """Create collection with an optional $jsonSchema validator, or update the
    validator on an existing collection. Uses validationLevel='moderate' so that
    pre-existing documents are never retroactively rejected."""
    existing = await db.list_collection_names()
    options = {}
    if validator is not None:
        options = {
            "validator": validator,
            "validationLevel": "moderate",
            "validationAction": "error",
        }
    if name not in existing:
        await db.create_collection(name, **options)
    elif validator is not None:
        try:
            await db.command({"collMod": name, **options})
        except OperationFailure:
            # If collMod is unsupported for any reason, skip (indexes still apply).
            pass


async def ensure_indexes(db, name: str, indexes: list[dict]) -> None:
    for spec in indexes:
        keys = spec["keys"]
        opts = {k: v for k, v in spec.items() if k != "keys"}
        try:
            await db[name].create_index(keys, **opts)
        except OperationFailure as e:
            # 85 IndexOptionsConflict / 86 IndexKeySpecsConflict: an equivalent
            # index already exists (e.g. created earlier under a default name).
            if getattr(e, "code", None) in (85, 86):
                continue
            raise


def schema(required, properties):
    """Build a permissive $jsonSchema (extra fields allowed, moderate level)."""
    return {
        "$jsonSchema": {
            "bsonType": "object",
            "required": required,
            "properties": properties,
        }
    }
