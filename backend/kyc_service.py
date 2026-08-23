"""KYC (Know Your Customer) service.

Security model:
- Document bytes are stored INSIDE MongoDB (kyc_documents.data as BSON Binary),
  never on a public/static path => there is NO public document URL.
- Documents are only ever returned through an authenticated endpoint that checks
  the caller is the OWNER or an ADMIN (see kyc_router.get_document).
- Optional ID number is stored ENCRYPTED (Fernet) and never returned in plaintext
  to anyone except... nobody. It is write-only; only "present/absent" is exposed.

KYC lifecycle: none -> pending -> (approved | rejected). After rejection the user
may resubmit (goes back to pending). KYC is NOT required to invest; it IS required
to withdraw (enforced in the withdrawal service).
"""
import os
import uuid
from datetime import datetime, timezone

from bson.binary import Binary
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

import notify_service
from db import db

# ---- File validation ----
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
ID_TYPES = {"aadhaar", "national_id", "passport", "other"}

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is None:
        key = os.environ.get("KYC_ENC_KEY")
        if not key:
            raise RuntimeError("KYC_ENC_KEY is not configured.")
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def _encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sniff_content(data: bytes) -> str | None:
    """Detect the real file type from magic bytes. Returns a MIME string or None.

    Prevents a client from spoofing Content-Type (e.g. uploading HTML/JS/SVG
    while claiming image/png) which could otherwise be a stored-XSS vector when
    the document is served back inline.
    """
    if len(data) < 4:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] == b"%PDF":
        return "application/pdf"
    return None


def validate_bytes(content_type: str, data: bytes) -> None:
    """Verify the actual bytes match an allowed type AND the claimed content_type."""
    sniffed = _sniff_content(data)
    if sniffed is None or sniffed not in ALLOWED_MIME or sniffed != content_type:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_file_content",
                    "message": "File content does not match an allowed image or PDF type."},
        )


def validate_upload(filename: str, content_type: str, size: int):
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_file_type",
                    "message": "Only JPG, PNG, WebP or PDF files are allowed."},
        )
    if size <= 0:
        raise HTTPException(status_code=400, detail={"code": "empty_file", "message": "File is empty."})
    if size > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail={"code": "file_too_large", "message": "Each file must be 5 MB or smaller."},
        )


async def get_record(user_id: str) -> dict | None:
    return await db.kyc_records.find_one({"user_id": user_id})


async def is_approved(user_id: str) -> bool:
    rec = await get_record(user_id)
    return bool(rec and rec.get("status") == "approved")


def serialize_status(rec: dict | None, docs: list | None = None) -> dict:
    if not rec:
        return {"status": "none", "id_type": None, "reject_reason": None,
                "can_submit": True, "submitted_at": None, "reviewed_at": None,
                "documents": []}
    status = rec.get("status", "none")
    doc_list = [
        {"id": d["id"], "doc_type": d["doc_type"], "mime": d.get("mime"),
         "uploaded_at": d.get("created_at")}
        for d in (docs or [])
    ]
    return {
        "status": status,
        "id_type": rec.get("id_type"),
        "id_number_present": bool(rec.get("id_number_encrypted")),
        "reject_reason": rec.get("reject_reason") if status == "rejected" else None,
        "submitted_at": rec.get("submitted_at"),
        "reviewed_at": rec.get("reviewed_at"),
        # user may (re)submit only when never submitted or previously rejected
        "can_submit": status in ("none", "rejected"),
        "documents": doc_list,
    }


async def get_status(user_id: str) -> dict:
    rec = await get_record(user_id)
    docs = []
    if rec:
        docs = [d async for d in db.kyc_documents.find(
            {"kyc_record_id": rec["id"]}, {"data": 0}
        )]
    return serialize_status(rec, docs)


async def submit(user_id: str, id_type: str, id_number: str | None,
                 id_doc: dict, selfie: dict) -> dict:
    """id_doc/selfie are dicts: {filename, content_type, bytes}."""
    if id_type not in ID_TYPES:
        raise HTTPException(status_code=400, detail={"code": "invalid_id_type",
                                                     "message": "Invalid ID type."})

    rec = await get_record(user_id)
    if rec and rec.get("status") in ("pending", "approved"):
        raise HTTPException(
            status_code=409,
            detail={"code": "already_" + rec["status"],
                    "message": "Your KYC is already " + rec["status"] + "."},
        )

    validate_upload(id_doc["filename"], id_doc["content_type"], len(id_doc["bytes"]))
    validate_upload(selfie["filename"], selfie["content_type"], len(selfie["bytes"]))
    # Defence-in-depth: verify real file signatures, not just the claimed type.
    validate_bytes(id_doc["content_type"], id_doc["bytes"])
    validate_bytes(selfie["content_type"], selfie["bytes"])

    ts = _now()
    record_id = rec["id"] if rec else str(uuid.uuid4())

    set_doc = {
        "status": "pending",
        "id_type": id_type,
        "submitted_at": ts,
        "updated_at": ts,
        "reject_reason": None,
        "admin_id": None,
        "reviewed_at": None,
    }
    if id_number:
        set_doc["id_number_encrypted"] = _encrypt(id_number.strip())

    await db.kyc_records.update_one(
        {"user_id": user_id},
        {"$set": set_doc,
         "$setOnInsert": {"id": record_id, "user_id": user_id, "created_at": ts}},
        upsert=True,
    )

    # Replace any prior documents for a clean resubmission.
    await db.kyc_documents.delete_many({"kyc_record_id": record_id})
    for doc_type, f in (("id_front", id_doc), ("selfie", selfie)):
        await db.kyc_documents.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "kyc_record_id": record_id,
            "doc_type": doc_type,
            "mime": f["content_type"],
            "size": len(f["bytes"]),
            "data": Binary(f["bytes"]),
            "file_path": None,
            "created_at": ts,
        })

    await notify_service.create(
        user_id=user_id, ntype="kyc_submitted",
        title="KYC submitted",
        body="Your identity verification was submitted and is pending review.",
        dedupe_key=f"kyc_submitted:{record_id}:{ts}",
    )
    return await get_status(user_id)


async def get_document_for(requester: dict, doc_id: str) -> dict:
    """Return a KYC document ONLY to its owner or an admin."""
    doc = await db.kyc_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    is_owner = doc["user_id"] == requester["id"]
    is_admin = requester.get("role") == "admin"
    if not (is_owner or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized to view this document.")
    return doc


# --------------------------- Admin ---------------------------

async def admin_list(status: str | None = None) -> list:
    q = {}
    if status:
        q["status"] = status
    out = []
    async for rec in db.kyc_records.find(q).sort("submitted_at", -1):
        user = await db.users.find_one({"id": rec["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        docs = [d async for d in db.kyc_documents.find(
            {"kyc_record_id": rec["id"]}, {"data": 0}
        )]
        out.append({
            "id": rec["id"],
            "user_id": rec["user_id"],
            "user_name": user.get("name") if user else None,
            "user_email": user.get("email") if user else None,
            "status": rec.get("status"),
            "id_type": rec.get("id_type"),
            "id_number_present": bool(rec.get("id_number_encrypted")),
            "reject_reason": rec.get("reject_reason"),
            "submitted_at": rec.get("submitted_at"),
            "reviewed_at": rec.get("reviewed_at"),
            "documents": [
                {"id": d["id"], "doc_type": d["doc_type"], "mime": d.get("mime")}
                for d in docs
            ],
        })
    return out


async def admin_approve(record_id: str, admin_id: str) -> dict:
    rec = await db.kyc_records.find_one({"id": record_id})
    if not rec:
        raise HTTPException(status_code=404, detail="KYC record not found.")
    if rec.get("status") != "pending":
        raise HTTPException(status_code=409,
                            detail={"code": "not_pending",
                                    "message": f"KYC is {rec.get('status')}, not pending."})
    ts = _now()
    await db.kyc_records.update_one(
        {"id": record_id},
        {"$set": {"status": "approved", "admin_id": admin_id, "reviewed_at": ts,
                  "reject_reason": None, "updated_at": ts}},
    )
    # Update user's kyc_status field so withdrawal enforcement works
    await db.users.update_one(
        {"id": rec["user_id"]},
        {"$set": {"kyc_status": "approved"}},
    )
    await notify_service.create(
        user_id=rec["user_id"], ntype="kyc_approved",
        title="KYC approved",
        body="Your identity verification was approved. You can now withdraw funds.",
        dedupe_key=f"kyc_approved:{record_id}:{ts}",
    )
    return {"ok": True, "status": "approved"}


async def admin_reject(record_id: str, admin_id: str, reason: str) -> dict:
    rec = await db.kyc_records.find_one({"id": record_id})
    if not rec:
        raise HTTPException(status_code=404, detail="KYC record not found.")
    if rec.get("status") != "pending":
        raise HTTPException(status_code=409,
                            detail={"code": "not_pending",
                                    "message": f"KYC is {rec.get('status')}, not pending."})
    reason = (reason or "").strip()
    if not reason:
        raise HTTPException(status_code=400,
                            detail={"code": "reason_required",
                                    "message": "A rejection reason is required."})
    ts = _now()
    await db.kyc_records.update_one(
        {"id": record_id},
        {"$set": {"status": "rejected", "admin_id": admin_id, "reviewed_at": ts,
                  "reject_reason": reason, "updated_at": ts}},
    )
    # Update user's kyc_status field
    await db.users.update_one(
        {"id": rec["user_id"]},
        {"$set": {"kyc_status": "rejected"}},
    )
    await notify_service.create(
        user_id=rec["user_id"], ntype="kyc_rejected",
        title="KYC rejected",
        body=f"Your identity verification was rejected: {reason}. Please resubmit.",
        dedupe_key=f"kyc_rejected:{record_id}:{ts}",
    )
    return {"ok": True, "status": "rejected"}
