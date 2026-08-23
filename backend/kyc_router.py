"""Authenticated KYC routes (user-facing).

Document bytes are served ONLY through get_document below, which enforces
owner-or-admin access. No public/static URL exists for KYC documents.
"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

import kyc_service
from deps import get_current_user

router = APIRouter(prefix="/api/kyc", tags=["kyc"])


@router.get("")
async def my_kyc(user: dict = Depends(get_current_user)):
    return await kyc_service.get_status(user["id"])


@router.post("/submit")
async def submit_kyc(
    id_type: str = Form(...),
    id_number: str | None = Form(default=None),
    id_document: UploadFile = File(...),
    selfie: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    id_bytes = await id_document.read()
    selfie_bytes = await selfie.read()
    return await kyc_service.submit(
        user["id"], id_type, id_number,
        {"filename": id_document.filename, "content_type": id_document.content_type, "bytes": id_bytes},
        {"filename": selfie.filename, "content_type": selfie.content_type, "bytes": selfie_bytes},
    )


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await kyc_service.get_document_for(user, doc_id)
    return Response(
        content=bytes(doc["data"]),
        media_type=doc.get("mime") or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="kyc-{doc["doc_type"]}"',
            "Cache-Control": "no-store, private",
        },
    )
