"""Auth routes mounted under /api/auth."""
from fastapi import APIRouter, Depends, Request

import auth_service
import maintenance_service
import rate_limit
import audit_service
from deps import get_current_user
from schemas import LoginIn, RegisterIn, TokenOut, UserOut
from security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(payload: RegisterIn, request: Request):
    # Throttle account creation per client IP (anti-abuse / anti-spam).
    rate_limit.enforce(f"register:ip:{rate_limit.client_ip(request)}", max_hits=100, window_seconds=3600)
    await maintenance_service.ensure_allowed("registration")
    user = await auth_service.register_user(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password=payload.password,
        referral_code=payload.referral_code,
    )
    token = create_access_token(subject=user["id"], role=user["role"])
    return TokenOut(access_token=token, user=UserOut(**auth_service.public_user(user)))


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, request: Request):
    # Brute-force protection: throttle per-IP AND per-target-email.
    ip = rate_limit.client_ip(request)
    email_key = f"login:email:{payload.email.strip().lower()}"
    rate_limit.enforce(f"login:ip:{ip}", max_hits=100, window_seconds=300)
    rate_limit.enforce(email_key, max_hits=10, window_seconds=300)
    user = await auth_service.authenticate_user(payload.email, payload.password)
    # Successful login clears the email bucket so legit users aren't locked out.
    rate_limit.reset(email_key)
    # Audit trail: record every successful ADMIN sign-in.
    if user.get("role") == "admin":
        await audit_service.log(
            "admin.login", actor=user, entity_type="user", entity_id=user["id"],
            meta={"ip": ip},
        )
    token = create_access_token(subject=user["id"], role=user["role"])
    return TokenOut(access_token=token, user=UserOut(**auth_service.public_user(user)))


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return UserOut(**auth_service.public_user(user))
