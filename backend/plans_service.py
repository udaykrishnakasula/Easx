"""Investment plan manager (admin).

Admins can edit plan terms (price, profit %, maturity %, lock period, name, active)
for NEW investments. Existing investments are NEVER affected because their terms
are snapshotted onto the investment document at purchase time (see invest_service).

Every edit:
  - bumps the plan `version`
  - appends a full before/after snapshot to the `plan_history` collection
  - is audit logged by the caller (admin_router)
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from db import db
from money import d128, fmt, to_dec

EDITABLE_DECIMAL = {"price", "profit_percentage", "maturity_percentage"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def serialize_plan(p: dict) -> dict:
    return {
        "id": p["id"],
        "key": p["key"],
        "name": p["name"],
        "price": fmt(p["price"]),
        "lock_days": int(p["lock_days"]),
        "profit_percentage": fmt(p["profit_percentage"]),
        "maturity_percentage": fmt(p["maturity_percentage"]),
        "display_order": int(p["display_order"]),
        "is_active": bool(p.get("is_active", True)),
        "version": int(p.get("version", 1)),
        "updated_at": p.get("updated_at"),
    }


async def list_plans() -> list:
    return [serialize_plan(p) async for p in db.investment_plans.find({}).sort("display_order", 1)]


async def get_plan(plan_key: str) -> dict:
    p = await db.investment_plans.find_one({"key": plan_key})
    if not p:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return p


async def update_plan(plan_key: str, patch: dict, admin_id: str) -> dict:
    plan = await get_plan(plan_key)

    to_set = {}
    for field in ("name",):
        if patch.get(field) is not None:
            val = str(patch[field]).strip()
            if not val:
                raise HTTPException(status_code=422, detail="Name cannot be empty.")
            to_set[field] = val
    for field in EDITABLE_DECIMAL:
        if patch.get(field) is not None:
            try:
                val = to_dec(patch[field])
            except Exception:
                raise HTTPException(status_code=422, detail=f"Invalid value for {field}.")
            if val < 0:
                raise HTTPException(status_code=422, detail=f"{field} cannot be negative.")
            if field == "price" and val <= 0:
                raise HTTPException(status_code=422, detail="Price must be positive.")
            to_set[field] = d128(val)
    if patch.get("lock_days") is not None:
        try:
            ld = int(patch["lock_days"])
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid lock period.")
        if ld < 1:
            raise HTTPException(status_code=422, detail="Lock period must be at least 1 day.")
        to_set["lock_days"] = ld
    if patch.get("is_active") is not None:
        to_set["is_active"] = bool(patch["is_active"])

    if not to_set:
        raise HTTPException(status_code=400, detail="No changes provided.")

    before = serialize_plan(plan)
    to_set["version"] = int(plan.get("version", 1)) + 1
    to_set["updated_at"] = _now()
    to_set["updated_by"] = admin_id
    await db.investment_plans.update_one({"key": plan_key}, {"$set": to_set})

    updated = await get_plan(plan_key)
    after = serialize_plan(updated)

    changed = {k: {"from": before.get(k), "to": after.get(k)}
               for k in after if before.get(k) != after.get(k) and k not in ("version", "updated_at")}
    await db.plan_history.insert_one({
        "id": str(uuid.uuid4()),
        "plan_key": plan_key,
        "version": after["version"],
        "changed": changed,
        "snapshot": after,
        "admin_id": admin_id,
        "created_at": _now(),
    })
    return after


async def plan_history(plan_key: str, limit: int = 100) -> list:
    out = []
    async for h in db.plan_history.find({"plan_key": plan_key}).sort("created_at", -1).limit(limit):
        h.pop("_id", None)
        out.append(h)
    return out
