"""In-app notification service.

Notifications are in-app only (channel="in_app"). Email is intentionally NOT used
for maturity notifications. Creation is idempotent via an optional `dedupe_key`
(unique sparse index) so the same logical notification is never created twice even
under worker retry / restart / concurrent jobs.
"""
import uuid
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from db import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create(
    user_id: str,
    ntype: str,
    title: str,
    body: str | None = None,
    dedupe_key: str | None = None,
    investment_id: str | None = None,
    channel: str = "in_app",
) -> bool:
    """Create an in-app notification. Returns True if a new one was created,
    False if it already existed (deduped)."""
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "channel": channel,
        "type": ntype,
        "title": title,
        "body": body,
        "is_read": False,
        "investment_id": investment_id,
        "created_at": _now(),
    }
    if dedupe_key:
        doc["dedupe_key"] = dedupe_key
    try:
        await db.notifications.insert_one(doc)
        return True
    except DuplicateKeyError:
        return False


def serialize(n: dict) -> dict:
    return {
        "id": n["id"],
        "type": n.get("type"),
        "title": n.get("title"),
        "body": n.get("body"),
        "is_read": bool(n.get("is_read", False)),
        "investment_id": n.get("investment_id"),
        "created_at": n.get("created_at"),
        "read_at": n.get("read_at"),
    }


async def list_for_user(user_id: str, unread_only: bool = False, limit: int = 50):
    q = {"user_id": user_id}
    if unread_only:
        q["is_read"] = False
    cur = db.notifications.find(q).sort("created_at", -1).limit(limit)
    return [serialize(n) async for n in cur]


async def unread_count(user_id: str) -> int:
    return await db.notifications.count_documents({"user_id": user_id, "is_read": False})


async def mark_read(user_id: str, notif_id: str) -> bool:
    res = await db.notifications.update_one(
        {"id": notif_id, "user_id": user_id},
        {"$set": {"is_read": True, "read_at": _now()}},
    )
    return res.modified_count == 1


async def mark_all_read(user_id: str) -> int:
    res = await db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "read_at": _now()}},
    )
    return res.modified_count
