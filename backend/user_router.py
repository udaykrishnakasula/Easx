"""Authenticated user routes: plans, investments, wallet, transactions, dashboard, notifications."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional

import invest_service
import deposit_service
import notify_service
import referral_service
import wallet_service
import maintenance_service
import withdrawal_service
from deps import get_current_user

router = APIRouter(prefix="/api", tags=["user"])


class BuyIn(BaseModel):
    plan_key: str = Field(pattern="^(silver|gold|platinum|diamond)$")
    idempotency_key: Optional[str] = Field(default=None, max_length=80)


class DepositIn(BaseModel):
    network: str = Field(pattern="^(TRC20|BEP20)$")
    amount: str = Field(min_length=1, max_length=32)
    tx_hash: str = Field(min_length=8, max_length=128)


class WithdrawIn(BaseModel):
    network: str = Field(pattern="^(TRC20|BEP20)$")
    amount: str = Field(min_length=1, max_length=32)
    to_address: str = Field(min_length=8, max_length=128)


@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    return await invest_service.get_dashboard(user)


@router.get("/plans")
async def plans(user: dict = Depends(get_current_user)):
    return await invest_service.get_plans_state(user["id"])


@router.post("/investments", status_code=201)
async def buy_investment(payload: BuyIn, user: dict = Depends(get_current_user)):
    await maintenance_service.ensure_allowed("investments")
    return await invest_service.buy_plan(user, payload.plan_key, payload.idempotency_key)


@router.get("/investments")
async def investments(plan_key: Optional[str] = Query(default=None),
                      user: dict = Depends(get_current_user)):
    return await invest_service.list_investments(user["id"], plan_key)


@router.get("/investments/{investment_id}")
async def investment_detail(investment_id: str, user: dict = Depends(get_current_user)):
    return await invest_service.get_investment(user["id"], investment_id)


@router.get("/deposits/config")
async def deposits_config(user: dict = Depends(get_current_user)):
    return await deposit_service.get_config()


@router.post("/deposits", status_code=201)
async def create_deposit(payload: DepositIn, user: dict = Depends(get_current_user)):
    await maintenance_service.ensure_allowed("deposits")
    return await deposit_service.create_deposit(user["id"], payload.network, payload.amount, payload.tx_hash)


@router.get("/deposits")
async def list_deposits(user: dict = Depends(get_current_user)):
    return await deposit_service.list_user(user["id"])


@router.get("/withdrawals/config")
async def withdrawals_config(user: dict = Depends(get_current_user)):
    return withdrawal_service.get_config()


@router.post("/withdrawals", status_code=201)
async def create_withdrawal(payload: WithdrawIn, user: dict = Depends(get_current_user)):
    await maintenance_service.ensure_allowed("withdrawals")
    return await withdrawal_service.create(user, payload.network, payload.amount, payload.to_address)


@router.get("/withdrawals")
async def list_withdrawals(user: dict = Depends(get_current_user)):
    return await withdrawal_service.list_user(user["id"])


@router.get("/wallet")
async def wallet(user: dict = Depends(get_current_user)):
    return await wallet_service.wallet_summary(user["id"])


@router.get("/referrals/summary")
async def referrals_summary(user: dict = Depends(get_current_user)):
    return await referral_service.summary(user)


@router.get("/wallet/consistency")
async def wallet_consistency(user: dict = Depends(get_current_user)):
    return await wallet_service.check_consistency(user["id"])


@router.get("/transactions")
async def transactions(limit: int = Query(default=50, le=200), skip: int = Query(default=0, ge=0),
                       user: dict = Depends(get_current_user)):
    return await wallet_service.list_transactions(user["id"], limit=limit, skip=skip)


@router.get("/rewards/feed")
async def rewards_feed(limit: int = Query(default=30, le=100),
                       since: Optional[str] = Query(default=None),
                       user: dict = Depends(get_current_user)):
    """Live activity feed of the user's rewards and payouts."""
    return await wallet_service.list_rewards_feed(user["id"], limit=limit, since=since)


@router.get("/notifications")
async def notifications(unread_only: bool = Query(default=False),
                        limit: int = Query(default=50, le=200),
                        user: dict = Depends(get_current_user)):
    return await notify_service.list_for_user(user["id"], unread_only=unread_only, limit=limit)


@router.get("/notifications/unread-count")
async def notifications_unread_count(user: dict = Depends(get_current_user)):
    return {"count": await notify_service.unread_count(user["id"])}


@router.post("/notifications/{notif_id}/read")
async def notification_read(notif_id: str, user: dict = Depends(get_current_user)):
    ok = await notify_service.mark_read(user["id"], notif_id)
    return {"ok": ok}


@router.post("/notifications/read-all")
async def notifications_read_all(user: dict = Depends(get_current_user)):
    return {"updated": await notify_service.mark_all_read(user["id"])}
