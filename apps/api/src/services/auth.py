"""
Auth service.

Responsibilities:
- Login: look up member by org_slug + handle, verify password, issue tokens
- Refresh: validate refresh token, re-issue access token
- Register: bootstrap-only member self-registration
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseService
from ..core.exceptions import (
    InvalidCredentials, NotFound, AlreadyExists, BootstrapOnly
)
from ..core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token,
    decode_token,
)
from ..models.org import Org, Member
from ..models.types import MemberState
from ..schemas.auth import (
    LoginRequest, LoginResponse, RefreshRequest, TokenResponse,
    RegisterMemberRequest, MemberSessionResponse,
)
from jose import JWTError


class AuthService(BaseService):

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, body: LoginRequest) -> LoginResponse:
        # 1. Resolve org by slug
        org = await self._get_org_by_slug(body.org_slug)
        if org is None:
            raise InvalidCredentials()

        # 2. Resolve member by handle within org
        member = await self._get_member_by_handle(org.id, body.handle)
        if member is None:
            raise InvalidCredentials()

        # 3. Verify password — same error regardless of which step failed
        if not member.password_hash or not verify_password(body.password, member.password_hash):
            raise InvalidCredentials()

        # 4. Issue tokens
        tokens = self._issue_tokens(member)

        return LoginResponse(
            tokens=tokens,
            member=MemberSessionResponse.model_validate(member),
        )

    # ── Token refresh ─────────────────────────────────────────────────────────

    async def refresh(self, body: RefreshRequest) -> TokenResponse:
        try:
            payload = decode_token(body.refresh_token)
            if payload.get("type") != "refresh":
                raise JWTError("not a refresh token")
        except JWTError:
            raise InvalidCredentials()

        member_id = uuid.UUID(payload["sub"])
        org_id = uuid.UUID(payload["org"])

        # Re-load member to get current state (state may have changed since token issued)
        member = await self.get_by_id(Member, member_id)
        if member is None or str(member.org_id) != str(org_id):
            raise InvalidCredentials()

        return self._issue_tokens(member)

    # ── Registration (bootstrap only) ─────────────────────────────────────────

    async def register(self, org_slug: str, body: RegisterMemberRequest) -> MemberSessionResponse:
        org = await self._get_org_by_slug(org_slug)
        if org is None:
            raise NotFound("Org", org_slug)

        # Registration is only permitted while org is in bootstrap
        if org.bootstrapped_at is not None:
            raise BootstrapOnly("member self-registration")

        # Unique handle within org
        existing = await self._get_member_by_handle(org.id, body.handle)
        if existing is not None:
            raise AlreadyExists("Member", "handle", body.handle)

        # Unique email within org
        existing_email = await self._get_member_by_email(org.id, body.email)
        if existing_email is not None:
            raise AlreadyExists("Member", "email", body.email)

        member = Member(
            org_id=org.id,
            handle=body.handle,
            display_name=body.display_name,
            email=body.email,
            password_hash=hash_password(body.password),
            joined_at=datetime.now(timezone.utc),
            current_state=MemberState.PROBATIONARY,
            proof_of_personhood_ref=body.proof_of_personhood_ref,
        )

        await self.save(member)
        return MemberSessionResponse.model_validate(member)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _issue_tokens(self, member: Member) -> TokenResponse:
        from ..core.config import get_settings
        settings = get_settings()
        access = create_access_token(
            str(member.id), str(member.org_id), member.current_state
        )
        refresh = create_refresh_token(str(member.id), str(member.org_id))
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def _get_org_by_slug(self, slug: str) -> Org | None:
        result = await self.db.execute(select(Org).where(Org.slug == slug))
        return result.scalar_one_or_none()

    async def _get_member_by_handle(self, org_id: uuid.UUID, handle: str) -> Member | None:
        result = await self.db.execute(
            select(Member).where(Member.org_id == org_id, Member.handle == handle)
        )
        return result.scalar_one_or_none()

    async def _get_member_by_email(self, org_id: uuid.UUID, email: str) -> Member | None:
        result = await self.db.execute(
            select(Member).where(Member.org_id == org_id, Member.email == email)
        )
        return result.scalar_one_or_none()
