"""Audit logging helper.

Every mutating admin action (suspend/unsuspend, approvals, rejections, wallet
adjustments, plan edits, settings and maintenance changes) writes an immutable
record to the `audit_logs` collection. Records are append-only and never mutated.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from db import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def log(
    action: str,
    actor: Optional[dict] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict:
    """Append an audit record. `actor` is the admin user dict (or None for system)."""
    doc = {
        "id": str(uuid.uuid4()),
        "action": action,
        "actor_id": (actor or {}).get("id"),
        "actor_role": (actor or {}).get("role"),
        "actor_email": (actor or {}).get("email"),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "meta": meta or {},
        "created_at": _now(),
    }
    await db.audit_logs.insert_one(doc)
    return doc


def serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


async def list_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = 200,
    skip: int = 0,
) -> list:
    query: dict = {}
    if action:
        query["action"] = action
    if entity_type:
        query["entity_type"] = entity_type
    if actor_id:
        query["actor_id"] = actor_id
    cur = db.audit_logs.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [serialize(d) async for d in cur]
