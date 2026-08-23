"""Maintenance mode + per-feature availability controls.

A single `maintenance_settings` document (id='maintenance') holds:
  - is_enabled: bool          -> GLOBAL maintenance mode (blocks user-facing writes)
  - message: str              -> shown to users
  - registration_enabled: bool
  - deposits_enabled: bool
  - investments_enabled: bool
  - withdrawals_enabled: bool

Guarantees:
  - Turning on maintenance / disabling a feature ONLY blocks NEW user actions
    (register, deposit, invest, withdraw). It NEVER touches existing investments,
    the maturity engine, or wallet balances (those run server-side, unaffected).
  - Every change is audit logged by the admin router.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status

from db import db

_ID = "maintenance"

# feature key -> settings field
FEATURES = {
    "registration": "registration_enabled",
    "deposits": "deposits_enabled",
    "investments": "investments_enabled",
    "withdrawals": "withdrawals_enabled",
}

_DEFAULTS = {
    "is_enabled": False,
    "message": "EasyX is under scheduled maintenance. Please check back soon.",
    "registration_enabled": True,
    "deposits_enabled": True,
    "investments_enabled": True,
    "withdrawals_enabled": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_settings() -> dict:
    """Return the maintenance doc, backfilling any missing fields with defaults."""
    doc = await db.maintenance_settings.find_one({"id": _ID})
    if not doc:
        doc = {"id": _ID, "created_at": _now(), "updated_at": _now(), "updated_by": None}
        doc.update(_DEFAULTS)
        await db.maintenance_settings.insert_one(dict(doc))
    # Backfill any newly-introduced fields on legacy docs.
    patch = {k: v for k, v in _DEFAULTS.items() if k not in doc}
    if patch:
        await db.maintenance_settings.update_one({"id": _ID}, {"$set": patch})
        doc.update(patch)
    doc.pop("_id", None)
    return doc


def public_status(doc: dict) -> dict:
    """Shape safe for unauthenticated clients (login/register screens)."""
    return {
        "is_enabled": bool(doc.get("is_enabled", False)),
        "message": doc.get("message") or _DEFAULTS["message"],
        "features": {
            key: bool(doc.get(field, True)) for key, field in FEATURES.items()
        },
    }


async def public() -> dict:
    return public_status(await get_settings())


ALLOWED_UPDATE_FIELDS = {"is_enabled", "message", *FEATURES.values()}


async def update(patch: dict, admin_id: str) -> dict:
    """Apply an admin update. Only whitelisted fields are written."""
    await get_settings()  # ensure the doc exists first
    to_set = {k: v for k, v in patch.items() if k in ALLOWED_UPDATE_FIELDS and v is not None}
    to_set["updated_at"] = _now()
    to_set["updated_by"] = admin_id
    await db.maintenance_settings.update_one({"id": _ID}, {"$set": to_set})
    return await get_settings()


async def ensure_allowed(feature: str) -> None:
    """Raise 503 if the app is in maintenance OR the given feature is disabled.

    `feature` must be one of FEATURES keys.
    """
    s = await get_settings()
    msg = s.get("message") or _DEFAULTS["message"]
    if s.get("is_enabled", False):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=msg)
    field = FEATURES.get(feature)
    if field and not s.get(field, True):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{feature.capitalize()} is temporarily unavailable. {msg}",
        )
