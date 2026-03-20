import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.members import MembersService
from ..schemas import (
    MemberResponse, MemberDetailResponse, UpdateMemberRequest,
    FeedItemResponse, Paginated, CuriosityResponse, SetCuriositiesRequest,
    NotificationResponse,
)

router = APIRouter(prefix="/members", tags=["members"])


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


@router.get("/{member_id}", response_model=MemberDetailResponse)
async def get_member(member_id: UUID, member: ActiveMember, db: DB):
    return await MembersService(db).get_member(
        member_id, _uuid.UUID(member.org_id)
    )
