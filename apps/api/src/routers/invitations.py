"""
Invitation join flow.

GET  /invitations/{token}        — public, returns invitation details
POST /invitations/{token}/accept — requires platform auth, creates membership
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..core.dependencies import DB, PlatformAuth
from ..core.events import get_event_bus, GovernanceEvent, EventType
from ..core.exceptions import NotFound
from ..core.security import create_org_session_token
from ..models.org import Org, Member, OrgInvitation, CircleMember, Circle, PlatformAccount
from ..models.types import MemberState

router = APIRouter(prefix="/invitations", tags=["invitations"])


class InvitationDetailResponse(BaseModel):
    invitation_id: uuid.UUID
    org_id: uuid.UUID
    org_name: str
    org_slug: str
    message: str | None = None
    invited_handle: str | None = None
    invited_email: str | None = None
    status: str
    expires_at: datetime | None = None


class InvitationAcceptResponse(BaseModel):
    org_id: uuid.UUID
    org_slug: str
    member_id: uuid.UUID
    circle_id: uuid.UUID | None = None
    org_session_token: str
    state: str


@router.get("/{token}", response_model=InvitationDetailResponse)
async def get_invitation(token: uuid.UUID, db: DB):
    inv = (await db.execute(
        select(OrgInvitation).where(OrgInvitation.id == token)
    )).scalar_one_or_none()

    if inv is None:
        raise HTTPException(status_code=404, detail="INVITATION_NOT_FOUND")
    if inv.status != "pending":
        raise HTTPException(status_code=410, detail=f"INVITATION_{inv.status.upper()}")
    if inv.expires_at and inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="INVITATION_EXPIRED")

    org = (await db.execute(
        select(Org).where(Org.id == inv.org_id)
    )).scalar_one_or_none()

    return InvitationDetailResponse(
        invitation_id=inv.id,
        org_id=inv.org_id,
        org_name=org.name if org else "Unknown",
        org_slug=org.slug if org else "",
        message=inv.message,
        invited_handle=inv.invited_handle,
        invited_email=inv.invited_email,
        status=inv.status,
        expires_at=inv.expires_at,
    )


class _AcceptBody(BaseModel):
    handle: str | None = None
    display_name: str | None = None


@router.post("/{token}/accept", response_model=InvitationAcceptResponse)
async def accept_invitation(
    token: uuid.UUID,
    body: _AcceptBody,
    auth: PlatformAuth,
    db: DB,
):
    account_id = uuid.UUID(auth.sub)

    inv = (await db.execute(
        select(OrgInvitation).where(OrgInvitation.id == token)
    )).scalar_one_or_none()

    if inv is None:
        raise HTTPException(status_code=404, detail="INVITATION_NOT_FOUND")
    if inv.status != "pending":
        raise HTTPException(status_code=410, detail=f"INVITATION_{inv.status.upper()}")
    if inv.expires_at and inv.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="INVITATION_EXPIRED")

    org = (await db.execute(
        select(Org).where(Org.id == inv.org_id)
    )).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="ORG_NOT_FOUND")

    existing_member = (await db.execute(
        select(Member).where(
            Member.org_id == inv.org_id,
            Member.platform_account_id == account_id,
        )
    )).scalar_one_or_none()

    if existing_member is not None:
        state_value = (
            existing_member.current_state.value
            if hasattr(existing_member.current_state, "value")
            else existing_member.current_state
        )
        token_val = create_org_session_token(
            account_id=str(account_id),
            member_id=str(existing_member.id),
            org_id=str(inv.org_id),
            member_state=state_value,
        )
        inv.status = "accepted"
        inv.platform_account_id = account_id
        inv.responded_at = datetime.now(timezone.utc)
        db.add(inv)
        await db.flush()

        return InvitationAcceptResponse(
            org_id=inv.org_id, org_slug=org.slug,
            member_id=existing_member.id, org_session_token=token_val,
            state=state_value,
        )

    account = (await db.execute(
        select(PlatformAccount).where(PlatformAccount.id == account_id)
    )).scalar_one_or_none()

    handle = body.handle or inv.invited_handle or (account.handle if account else None)
    display_name = body.display_name or (inv.invited_handle or account.handle if account else "member")

    if handle is None:
        raise HTTPException(status_code=400, detail="HANDLE_REQUIRED")

    handle_exists = (await db.execute(
        select(Member).where(Member.org_id == inv.org_id, Member.handle == handle)
    )).scalar_one_or_none()
    if handle_exists is not None:
        raise HTTPException(status_code=409, detail="HANDLE_TAKEN_IN_ORG")

    now = datetime.now(timezone.utc)
    member = Member(
        org_id=inv.org_id,
        handle=handle,
        display_name=display_name,
        email=inv.invited_email or (account.email if account else None),
        platform_account_id=account_id,
        joined_at=now,
        current_state=MemberState.PROBATIONARY,
    )
    db.add(member)
    await db.flush()

    circles_result = await db.execute(
        select(Circle.id).where(
            Circle.org_id == inv.org_id,
            Circle.founding_circle == True,
            Circle.dissolved_at.is_(None),
        ).limit(1)
    )
    circle_id = circles_result.scalar_one_or_none()

    if circle_id:
        cm = CircleMember(
            circle_id=circle_id, member_id=member.id,
            joined_at=now, current_state=MemberState.PROBATIONARY,
        )
        db.add(cm)
        await db.flush()

    inv.status = "accepted"
    inv.platform_account_id = account_id
    inv.responded_at = now
    db.add(inv)
    await db.flush()

    await get_event_bus().emit(
        inv.org_id,
        GovernanceEvent(
            event_type=EventType.MEMBER_REGISTERED,
            subject_id=member.id,
            subject_type="member",
            payload={
                "handle": member.handle,
                "joined_at": member.joined_at.isoformat(),
                "invitation_id": str(inv.id),
            },
        ),
    )

    state_value = member.current_state.value if hasattr(member.current_state, "value") else member.current_state
    token_val = create_org_session_token(
        account_id=str(account_id),
        member_id=str(member.id),
        org_id=str(inv.org_id),
        member_state=state_value,
    )

    return InvitationAcceptResponse(
        org_id=inv.org_id, org_slug=org.slug,
        member_id=member.id, circle_id=circle_id,
        org_session_token=token_val, state=state_value,
    )
