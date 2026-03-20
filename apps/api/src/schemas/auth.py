from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator

from .common import OrmBase
from ..models.types import MemberState


# ── Requests ──────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    org_slug: str = Field(..., min_length=2, max_length=100)
    handle: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterMemberRequest(BaseModel):
    """
    Bootstrap step 3 — member self-registration.
    Only valid while bootstrapped_at is null.
    """
    handle: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9_-]+$")
    display_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=10)
    proof_of_personhood_ref: str | None = Field(
        None,
        max_length=500,
        description="External reference — URL, document ID, or credential reference",
    )


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=10)


# ── Responses ─────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class MemberSessionResponse(OrmBase):
    """Returned alongside TokenResponse on login — avoids a separate /me call."""
    id: uuid.UUID
    handle: str
    display_name: str
    org_id: uuid.UUID
    current_state: MemberState
    joined_at: datetime


class LoginResponse(BaseModel):
    tokens: TokenResponse
    member: MemberSessionResponse
