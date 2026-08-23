"""Pydantic request/response models for auth (Phase 1)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    referral_code: Optional[str] = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def _clean_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "")
        if not v.replace("+", "").isdigit():
            raise ValueError("phone must contain only digits and an optional leading +")
        return v

    @field_validator("referral_code")
    @classmethod
    def _clean_ref(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        return v or None


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    email: EmailStr
    phone: str
    role: str
    email_verified: bool
    kyc_status: str
    referral_code: str
    referred_by: Optional[str] = None
    status: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
