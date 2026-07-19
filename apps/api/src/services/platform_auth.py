"""
Platform authentication service.

Handles the human-level identity layer: registration, login, and the
"enter org" exchange that converts a platform token into an org session
token for a specific membership.

This sits ABOVE the existing org-scoped auth.py service, which still
handles org-side concerns: bootstrap-only registration (founding members),
and is now also called internally by enter_org() to mint org session tokens.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseService
from ..core.exceptions import AlreadyExists, Forbidden, NotFound
from ..core.security import (
    hash_password, verify_password,
    create_platform_token, create_platform_refresh_token,
    create_org_session_token,
)
from ..models.org import Member, Org, PlatformAccount


class PlatformAuthService(BaseService):

    # ── Registration ─────────────────────────────────────────────────────────

    async def register(
        self, handle: str, email: str, password: str,
        legal_name: str | None = None,
    ) -> dict:
        """
        Create a platform account. This is the ONLY signup surface — there is
        no more "register into org X" path for ordinary members. Founding
        members during bootstrap still go through org-scoped /auth/register,
        which internally creates a platform account too (see auth.py).
        """
        existing = (await self.db.execute(
            select(PlatformAccount).where(
                or_(PlatformAccount.handle == handle, PlatformAccount.email == email)
            )
        )).scalar_one_or_none()
        if existing:
            raise AlreadyExists("PlatformAccount", "handle/email", handle)

        now = datetime.now(timezone.utc)
        account = PlatformAccount(
            handle=handle,
            email=email,
            password_hash=hash_password(password),
            legal_name=legal_name,
            legal_name_changed_at=now if legal_name else None,
            created_at=now,
        )
        self.db.add(account)
        await self.db.flush()

        return {
            "account_id": str(account.id),
            "handle": account.handle,
            "tokens": {
                "access_token":  create_platform_token(str(account.id)),
                "refresh_token": create_platform_refresh_token(str(account.id)),
            },
        }

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, handle_or_email: str, password: str) -> dict:
        account = (await self.db.execute(
            select(PlatformAccount).where(
                or_(
                    PlatformAccount.handle == handle_or_email,
                    PlatformAccount.email == handle_or_email,
                )
            )
        )).scalar_one_or_none()
        if account is None or not verify_password(password, account.password_hash):
            raise Forbidden("INVALID_CREDENTIALS")

        account.last_seen_at = datetime.now(timezone.utc)
        self.db.add(account)
        await self.db.flush()

        return {
            "account": {
                "id": str(account.id),
                "handle": account.handle,
                "legal_name": account.legal_name,
            },
            "tokens": {
                "access_token":  create_platform_token(str(account.id)),
                "refresh_token": create_platform_refresh_token(str(account.id)),
            },
        }

    # ── Org memberships for the personal dashboard ──────────────────────────

    async def list_my_orgs(self, account_id: uuid.UUID) -> list[dict]:
        rows = (await self.db.execute(
            select(Member, Org)
            .join(Org, Org.id == Member.org_id)
            .where(Member.platform_account_id == account_id)
        )).all()

        return [
            {
                "org_id":   str(org.id),
                "org_slug": org.slug,
                "org_name": org.name,
                "member_id": str(member.id),
                "display_name_org": member.display_name_org or member.display_name,
                "current_state": member.current_state.value
                    if hasattr(member.current_state, "value") else member.current_state,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            }
            for member, org in rows
        ]

    # ── Enter org: exchange platform token for org session token ────────────

    async def enter_org(self, account_id: uuid.UUID, org_id: uuid.UUID) -> dict:
        """
        The "switch into this org" action. Requires an existing membership
        linked to this platform account — does not create one.
        """
        member = (await self.db.execute(
            select(Member).where(
                Member.org_id == org_id,
                Member.platform_account_id == account_id,
            )
        )).scalar_one_or_none()
        if member is None:
            raise NotFound("Membership", f"account={account_id} org={org_id}")

        state_value = (
            member.current_state.value
            if hasattr(member.current_state, "value") else member.current_state
        )

        token = create_org_session_token(
            account_id=str(account_id),
            member_id=str(member.id),
            org_id=str(org_id),
            member_state=state_value,
        )

        return {
            "org_session_token": token,
            "member_id": str(member.id),
            "org_id": str(org_id),
            "state": state_value,
        }

    # ── Link an existing org membership to a platform account ───────────────
    # Used during the transition period and for bootstrap (first member of
    # a new org gets both created together — see bootstrap/service.py).

    async def link_membership(
        self, account_id: uuid.UUID, member_id: uuid.UUID, org_id: uuid.UUID,
    ) -> None:
        member = (await self.db.execute(
            select(Member).where(Member.id == member_id, Member.org_id == org_id)
        )).scalar_one_or_none()
        if member is None:
            raise NotFound("Member", str(member_id))
        member.platform_account_id = account_id
        self.db.add(member)
        await self.db.flush()
