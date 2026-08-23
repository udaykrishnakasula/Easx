"""Admin routes: manual wallet adjustment + automatic-maturity operations.

Guarded by require_admin. All wallet actions are ledgered. The maturity endpoints
let an admin trigger the sweep on demand and (for ops/testing) backdate or
force-mature a specific investment. All maturity operations remain idempotent.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional

import invest_service
import deposit_service
import maturity_service
import wallet_service
import kyc_service
import referral_service
import audit_service
import maintenance_service
import notify_service
import plans_service
import withdrawal_service
import admin_stats_service
import reports_service
from db import db
from deps import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/reports")
async def list_reports(admin: dict = Depends(require_admin)):
    """List the datasets an admin can export."""
    return {"datasets": reports_service.DATASETS, "formats": ["csv", "xlsx"]}


@router.get("/reports/{dataset}")
async def export_report(dataset: str, format: str = "csv", admin: dict = Depends(require_admin)):
    """Export a dataset as CSV or XLSX (admin-only)."""
    if dataset not in reports_service.DATASETS:
        raise HTTPException(status_code=404, detail=f"Unknown dataset '{dataset}'.")
    fmt_lower = (format or "csv").lower()
    if fmt_lower not in ("csv", "xlsx"):
        raise HTTPException(status_code=400, detail="format must be 'csv' or 'xlsx'.")

    headers, rows = await reports_service.build_dataset(dataset)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    await audit_service.log(
        "report.export", actor=admin, entity_type="report", entity_id=dataset,
        meta={"format": fmt_lower, "row_count": len(rows)},
    )

    if fmt_lower == "csv":
        content = reports_service.to_csv_bytes(headers, rows)
        media_type = "text/csv"
        filename = f"easyx-{dataset}-{ts}.csv"
    else:
        content = reports_service.to_xlsx_bytes(headers, rows, sheet_name=dataset)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"easyx-{dataset}-{ts}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class AdjustIn(BaseModel):
    user_id: str
    amount: str = Field(description="Positive decimal string")
    direction: str = Field(pattern="^(credit|debit)$")
    note: Optional[str] = Field(default=None, max_length=200)
    idempotency_key: Optional[str] = Field(default=None, max_length=80)


@router.post("/wallet/adjust")
async def adjust_wallet(payload: AdjustIn, admin: dict = Depends(require_admin)):
    target = await db.users.find_one({"id": payload.user_id})
    if not target:
        return {"error": "user_not_found"}
    key = payload.idempotency_key or f"adjust:{uuid.uuid4()}"
    tx_type = "ADMIN_ADJUSTMENT"
    fn = wallet_service.credit if payload.direction == "credit" else wallet_service.debit
    tx = await fn(
        payload.user_id, payload.amount, tx_type=tx_type,
        ref_type="admin", ref_id=admin["id"],
        idempotency_key=key, note=payload.note or "Admin adjustment",
    )
    await audit_service.log(
        "wallet.adjust", actor=admin, entity_type="user", entity_id=payload.user_id,
        meta={"direction": payload.direction, "amount": payload.amount, "note": payload.note},
    )
    return wallet_service.serialize_tx(tx)


@router.post("/maturity/run")
async def maturity_run(admin: dict = Depends(require_admin)):
    """Trigger the maturity sweep now (matures all ACTIVE investments past due)."""
    return await maturity_service.run_maturity_sweep()


@router.post("/maturity/reminders/run")
async def maturity_reminders_run(admin: dict = Depends(require_admin)):
    """Trigger the 7/3/1-day reminder sweep now."""
    return await maturity_service.run_reminder_sweep()


@router.post("/investments/{inv_id}/mature")
async def force_mature(inv_id: str, admin: dict = Depends(require_admin)):
    """Force-mature a specific investment immediately (idempotent — a second call
    performs no additional payout)."""
    inv = await db.investments.find_one({"id": inv_id})
    if not inv:
        return {"error": "investment_not_found"}
    performed = await maturity_service.mature_investment(inv)
    fresh = await db.investments.find_one({"id": inv_id})
    return {"performed_payout": performed, "investment": invest_service.serialize_investment(fresh)}


class BackdateIn(BaseModel):
    seconds_ago: int = Field(default=1, ge=0, description="Set maturity_at this many seconds in the past")


@router.post("/investments/{inv_id}/backdate")
async def backdate_investment(inv_id: str, payload: BackdateIn, admin: dict = Depends(require_admin)):
    """Ops/testing helper: move an investment's maturity_at into the past so the
    automatic sweep will pick it up on its next run."""
    inv = await db.investments.find_one({"id": inv_id})
    if not inv:
        return {"error": "investment_not_found"}
    new_maturity = (datetime.now(timezone.utc) - timedelta(seconds=payload.seconds_ago)).isoformat()
    await db.investments.update_one(
        {"id": inv_id},
        {"$set": {"maturity_at": new_maturity, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "maturity_at": new_maturity}


# --------------------------- Deposits (manual verification) ---------------------------

class ApproveDepositIn(BaseModel):
    approved_amount: Optional[str] = Field(default=None, description="Optional override; defaults to submitted amount")
    note: Optional[str] = Field(default=None, max_length=300)


class RejectDepositIn(BaseModel):
    note: Optional[str] = Field(default=None, max_length=300)


class DepositAddressesIn(BaseModel):
    trc20: str = Field(min_length=6, max_length=128)
    bep20: str = Field(min_length=6, max_length=128)


@router.get("/deposits")
async def admin_list_deposits(status: Optional[str] = None, admin: dict = Depends(require_admin)):
    return await deposit_service.admin_list(status)


@router.post("/deposits/{deposit_id}/approve")
async def admin_approve_deposit(deposit_id: str, payload: ApproveDepositIn, admin: dict = Depends(require_admin)):
    result = await deposit_service.approve(deposit_id, admin["id"], payload.approved_amount, payload.note)
    await audit_service.log(
        "deposit.approve", actor=admin, entity_type="deposit", entity_id=deposit_id,
        meta={"approved_amount": payload.approved_amount, "note": payload.note},
    )
    return result


@router.post("/deposits/{deposit_id}/reject")
async def admin_reject_deposit(deposit_id: str, payload: RejectDepositIn, admin: dict = Depends(require_admin)):
    result = await deposit_service.reject(deposit_id, admin["id"], payload.note)
    await audit_service.log(
        "deposit.reject", actor=admin, entity_type="deposit", entity_id=deposit_id,
        meta={"reason": payload.note},
    )
    return result


@router.get("/settings/deposit")
async def admin_get_deposit_settings(admin: dict = Depends(require_admin)):
    return await deposit_service.get_config()


@router.put("/settings/deposit")
async def admin_set_deposit_settings(payload: DepositAddressesIn, admin: dict = Depends(require_admin)):
    return await deposit_service.set_deposit_addresses(payload.trc20, payload.bep20, admin["id"])


# --------------------------- KYC (manual review) ---------------------------

class RejectKycIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.get("/kyc")
async def admin_list_kyc(status: Optional[str] = None, admin: dict = Depends(require_admin)):
    return await kyc_service.admin_list(status)


@router.post("/kyc/{record_id}/approve")
async def admin_approve_kyc(record_id: str, admin: dict = Depends(require_admin)):
    result = await kyc_service.admin_approve(record_id, admin["id"])
    await audit_service.log(
        "kyc.approve", actor=admin, entity_type="kyc_record", entity_id=record_id,
    )
    return result


@router.post("/kyc/{record_id}/reject")
async def admin_reject_kyc(record_id: str, payload: RejectKycIn, admin: dict = Depends(require_admin)):
    result = await kyc_service.admin_reject(record_id, admin["id"], payload.reason)
    await audit_service.log(
        "kyc.reject", actor=admin, entity_type="kyc_record", entity_id=record_id,
        meta={"reason": payload.reason},
    )
    return result


@router.get("/kyc/documents/{doc_id}")
async def admin_get_kyc_document(doc_id: str, admin: dict = Depends(require_admin)):
    from fastapi.responses import Response
    doc = await kyc_service.get_document_for(admin, doc_id)
    return Response(
        content=bytes(doc["data"]),
        media_type=doc.get("mime") or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="kyc-{doc["doc_type"]}"',
                 "Cache-Control": "no-store, private"},
    )


# --------------------------- Referrals (overview) ---------------------------

@router.get("/referrals")
async def admin_referrals_overview(admin: dict = Depends(require_admin)):
    return await referral_service.admin_overview()


# --------------------------- Users (view / suspend / unsuspend) ---------------------------

def _serialize_user(u: dict) -> dict:
    u = dict(u)
    u.pop("_id", None)
    u.pop("password_hash", None)
    return u


@router.get("/users")
async def admin_list_users(
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    admin: dict = Depends(require_admin),
):
    """List users (excludes admins) with wallet balance. Optional status filter and
    text search across name/email/phone/referral_code."""
    query: dict = {"role": {"$ne": "admin"}}
    if status:
        query["status"] = status
    if q:
        rx = {"$regex": q.strip(), "$options": "i"}
        query["$or"] = [
            {"name": rx}, {"email": rx}, {"phone": rx}, {"referral_code": rx},
        ]
    total = await db.users.count_documents(query)
    cur = db.users.find(query).sort("created_at", -1).skip(max(skip, 0)).limit(min(max(limit, 1), 200))
    users = []
    async for u in cur:
        row = _serialize_user(u)
        wallet = await db.wallets.find_one({"user_id": u["id"]})
        row["wallet"] = wallet_service.serialize_wallet(wallet) if wallet else None
        users.append(row)
    return {"total": total, "users": users}


@router.get("/users/{user_id}")
async def admin_get_user(user_id: str, admin: dict = Depends(require_admin)):
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")
    row = _serialize_user(u)
    wallet = await db.wallets.find_one({"user_id": user_id})
    row["wallet"] = wallet_service.serialize_wallet(wallet) if wallet else None
    row["investment_count"] = await db.investments.count_documents({"user_id": user_id})
    row["active_investment_count"] = await db.investments.count_documents(
        {"user_id": user_id, "status": "active"}
    )
    return row


class SuspendIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/users/{user_id}/suspend")
async def admin_suspend_user(user_id: str, payload: SuspendIn, admin: dict = Depends(require_admin)):
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")
    if u.get("role") == "admin":
        raise HTTPException(status_code=400, detail="Admin accounts cannot be suspended.")
    if u.get("status") == "suspended":
        raise HTTPException(status_code=400, detail="User is already suspended.")

    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "status": "suspended",
            "suspended_at": now,
            "suspended_reason": payload.reason,
            "suspended_by": admin["id"],
            "updated_at": now,
        }},
    )
    await audit_service.log(
        "user.suspend", actor=admin, entity_type="user", entity_id=user_id,
        meta={"reason": payload.reason},
    )
    await notify_service.create(
        user_id, "account_suspended", "Account suspended",
        body="Your account has been suspended. Existing investments continue toward maturity. Contact support for details.",
    )
    fresh = await db.users.find_one({"id": user_id})
    return _serialize_user(fresh)


@router.post("/users/{user_id}/unsuspend")
async def admin_unsuspend_user(user_id: str, admin: dict = Depends(require_admin)):
    u = await db.users.find_one({"id": user_id})
    if not u:
        raise HTTPException(status_code=404, detail="User not found.")
    if u.get("status") != "suspended":
        raise HTTPException(status_code=400, detail="User is not suspended.")

    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"status": "active", "updated_at": now},
         "$unset": {"suspended_at": "", "suspended_reason": "", "suspended_by": ""}},
    )
    await audit_service.log(
        "user.unsuspend", actor=admin, entity_type="user", entity_id=user_id,
    )
    await notify_service.create(
        user_id, "account_reactivated", "Account reactivated",
        body="Your account has been reactivated. Welcome back!",
    )
    fresh = await db.users.find_one({"id": user_id})
    return _serialize_user(fresh)


# --------------------------- Maintenance mode + feature switches ---------------------------

class MaintenanceIn(BaseModel):
    is_enabled: Optional[bool] = None
    message: Optional[str] = Field(default=None, max_length=500)
    registration_enabled: Optional[bool] = None
    deposits_enabled: Optional[bool] = None
    investments_enabled: Optional[bool] = None
    withdrawals_enabled: Optional[bool] = None


@router.get("/maintenance")
async def admin_get_maintenance(admin: dict = Depends(require_admin)):
    return await maintenance_service.get_settings()


@router.put("/maintenance")
async def admin_update_maintenance(payload: MaintenanceIn, admin: dict = Depends(require_admin)):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="No changes provided.")
    updated = await maintenance_service.update(patch, admin["id"])
    await audit_service.log(
        "maintenance.update", actor=admin, entity_type="maintenance_settings",
        entity_id="maintenance", meta=patch,
    )
    return updated


# --------------------------- Audit logs (read-only) ---------------------------

@router.get("/audit-logs")
async def admin_list_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 200,
    skip: int = 0,
    admin: dict = Depends(require_admin),
):
    return await audit_service.list_logs(
        action=action, entity_type=entity_type,
        limit=min(max(limit, 1), 500), skip=max(skip, 0),
    )


# --------------------------- Overview / KPIs ---------------------------

@router.get("/overview")
async def admin_overview_stats(admin: dict = Depends(require_admin)):
    return await admin_stats_service.overview()


# --------------------------- Investment Plans (editor + history) ---------------------------

class PlanUpdateIn(BaseModel):
    name: Optional[str] = Field(default=None, max_length=60)
    price: Optional[str] = Field(default=None, max_length=32)
    profit_percentage: Optional[str] = Field(default=None, max_length=32)
    maturity_percentage: Optional[str] = Field(default=None, max_length=32)
    lock_days: Optional[int] = Field(default=None, ge=1, le=3650)
    is_active: Optional[bool] = None


@router.get("/plans")
async def admin_list_plans(admin: dict = Depends(require_admin)):
    return await plans_service.list_plans()


@router.put("/plans/{plan_key}")
async def admin_update_plan(plan_key: str, payload: PlanUpdateIn, admin: dict = Depends(require_admin)):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = await plans_service.update_plan(plan_key, patch, admin["id"])
    await audit_service.log(
        "plan.update", actor=admin, entity_type="investment_plan", entity_id=plan_key, meta=patch,
    )
    return updated


@router.get("/plans/{plan_key}/history")
async def admin_plan_history(plan_key: str, admin: dict = Depends(require_admin)):
    return await plans_service.plan_history(plan_key)


# --------------------------- Investments (view / cancel + refund) ---------------------------

class CancelInvestmentIn(BaseModel):
    refund_amount: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=3, max_length=300)


@router.get("/investments")
async def admin_list_investments(
    status: Optional[str] = None,
    q: Optional[str] = None,
    admin: dict = Depends(require_admin),
):
    return await invest_service.admin_list_investments(status_filter=status, q=q)


@router.post("/investments/{investment_id}/cancel")
async def admin_cancel_investment(investment_id: str, payload: CancelInvestmentIn, admin: dict = Depends(require_admin)):
    result = await invest_service.admin_cancel(
        investment_id, payload.refund_amount, payload.reason, admin["id"],
    )
    await audit_service.log(
        "investment.cancel", actor=admin, entity_type="investment", entity_id=investment_id,
        meta={"refund_amount": payload.refund_amount, "reason": payload.reason},
    )
    return result


# --------------------------- Withdrawals (approve / reject / process) ---------------------------

class WithdrawalNoteIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=300)


class WithdrawalProcessIn(BaseModel):
    tx_hash: str = Field(min_length=8, max_length=128)


@router.get("/withdrawals")
async def admin_list_withdrawals(status: Optional[str] = None, admin: dict = Depends(require_admin)):
    return await withdrawal_service.admin_list(status=status)


@router.post("/withdrawals/{withdrawal_id}/approve")
async def admin_approve_withdrawal(withdrawal_id: str, payload: WithdrawalNoteIn, admin: dict = Depends(require_admin)):
    result = await withdrawal_service.approve(withdrawal_id, admin["id"], note=payload.reason)
    await audit_service.log(
        "withdrawal.approve", actor=admin, entity_type="withdrawal", entity_id=withdrawal_id,
    )
    return result


@router.post("/withdrawals/{withdrawal_id}/reject")
async def admin_reject_withdrawal(withdrawal_id: str, payload: WithdrawalNoteIn, admin: dict = Depends(require_admin)):
    result = await withdrawal_service.reject(withdrawal_id, admin["id"], note=payload.reason)
    await audit_service.log(
        "withdrawal.reject", actor=admin, entity_type="withdrawal", entity_id=withdrawal_id,
        meta={"reason": payload.reason},
    )
    return result


@router.post("/withdrawals/{withdrawal_id}/process")
async def admin_process_withdrawal(withdrawal_id: str, payload: WithdrawalProcessIn, admin: dict = Depends(require_admin)):
    result = await withdrawal_service.process(withdrawal_id, admin["id"], payload.tx_hash)
    await audit_service.log(
        "withdrawal.process", actor=admin, entity_type="withdrawal", entity_id=withdrawal_id,
        meta={"tx_hash": payload.tx_hash},
    )
    return result

