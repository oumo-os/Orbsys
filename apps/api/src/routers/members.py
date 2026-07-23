import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel as _BaseModel

from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.members import MembersService
from ..schemas import (
    MemberResponse, MemberDetailResponse, UpdateMemberRequest,
    FeedItemResponse, Paginated, CuriosityResponse, SetCuriositiesRequest,
    NotificationResponse,
)

router = APIRouter(prefix="/members", tags=["members"])


@router.get("", response_model=Paginated[MemberResponse])
async def list_members(
    member: ActiveMember, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    """List all members in the organisation."""
    return await MembersService(db).list_members(
        _uuid.UUID(member.org_id), page, page_size
    )


class _ApplyRequest(_BaseModel):
    handle: str
    display_name: str
    email: str
    password: str
    motivation: str | None = None
    expertise_summary: str | None = None
    proof_of_personhood_ref: str | None = None


class _ReviewRequest(_BaseModel):
    approve: bool
    note: str | None = None


@router.get("/me", response_model=MemberDetailResponse)
async def get_me(member: ActiveMember, db: DB):
    return await MembersService(db).get_me(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id)
    )


@router.patch("/me", response_model=MemberResponse)
async def update_me(body: UpdateMemberRequest, member: ActiveMember, db: DB):
    return await MembersService(db).update_me(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id), body
    )


@router.get("/me/feed", response_model=Paginated[FeedItemResponse])
async def get_feed(
    member: ActiveMember, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    return await MembersService(db).get_feed(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id), page, page_size
    )


@router.get("/me/curiosities", response_model=list[CuriosityResponse])
async def get_curiosities(member: ActiveMember, db: DB):
    return await MembersService(db).get_curiosities(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id)
    )


@router.put("/me/curiosities", response_model=list[CuriosityResponse])
async def set_curiosities(body: SetCuriositiesRequest, member: ActiveMember, db: DB):
    return await MembersService(db).set_curiosities(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id), body
    )


@router.get("/me/notifications", response_model=Paginated[NotificationResponse])
async def get_notifications(
    member: ActiveMember, db: DB,
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    return await MembersService(db).get_notifications(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id),
        unread_only, page, page_size,
    )


@router.post("/me/notifications/{notification_id}/read", status_code=204)
async def mark_read(notification_id: UUID, member: ActiveMember, db: DB):
    await MembersService(db).mark_notification_read(
        notification_id, _uuid.UUID(member.member_id), _uuid.UUID(member.org_id)
    )


@router.post("/me/notifications/read-all", status_code=204)
async def mark_all_read(member: ActiveMember, db: DB):
    await MembersService(db).mark_all_notifications_read(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id)
    )


@router.post("/apply", status_code=202)
async def apply_to_join(
    body: _ApplyRequest,
    db: DB,
    org_slug: str = Query(..., description="Target org slug"),
):
    """
    Submit a membership application.
    Only works post-bootstrap (bootstrapped_at is set).
    Returns 403 if membership_policy is invite_only or closed.
    """
    from ..models.org import Org
    from sqlalchemy import select
    org = (await db.execute(
        select(Org).where(Org.slug == org_slug)
    )).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Org not found")
    return await MembersService(db).apply_to_join(
        org_id=org.id,
        handle=body.handle,
        display_name=body.display_name,
        email=body.email,
        password=body.password,
        motivation=body.motivation,
        expertise_summary=body.expertise_summary,
        proof_of_personhood_ref=body.proof_of_personhood_ref,
    )


@router.get("/applications")
async def list_applications(
    member: GovWriter,
    db: DB,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    """Membership Circle review queue."""
    return await MembersService(db).list_applications(
        _uuid.UUID(member.org_id), status_filter, page, page_size
    )


@router.post("/applications/{application_id}/review")
async def review_application(
    application_id: UUID,
    body: _ReviewRequest,
    member: GovWriter,
    db: DB,
):
    return await MembersService(db).review_application(
        application_id=_uuid.UUID(str(application_id)),
        org_id=_uuid.UUID(member.org_id),
        reviewer_id=_uuid.UUID(member.member_id),
        approve=body.approve,
        note=body.note,
    )


@router.get("/{member_id}", response_model=MemberDetailResponse)
async def get_member(member_id: UUID, member: ActiveMember, db: DB):
    return await MembersService(db).get_member(
        member_id, _uuid.UUID(member.org_id)
    )
