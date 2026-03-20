import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.circles import CirclesService
from ..schemas import (
    CircleResponse, CircleSummaryResponse, CircleMemberResponse,
    CircleHealthSnapshotResponse, InviteMemberRequest, InvitationResponse,
)

router = APIRouter(prefix="/circles", tags=["circles"])


@router.get("", response_model=list[CircleSummaryResponse])
async def list_circles(member: ActiveMember, db: DB):
    return await CirclesService(db).list_circles(_uuid.UUID(member.org_id))


@router.get("/{circle_id}", response_model=CircleResponse)
async def get_circle(circle_id: UUID, member: ActiveMember, db: DB):
    return await CirclesService(db).get_circle(circle_id, _uuid.UUID(member.org_id))


@router.get("/{circle_id}/members", response_model=list[CircleMemberResponse])
async def list_circle_members(circle_id: UUID, member: ActiveMember, db: DB):
    return await CirclesService(db).list_circle_members(circle_id, _uuid.UUID(member.org_id))


@router.post("/{circle_id}/members", response_model=InvitationResponse, status_code=201)
async def invite_member(circle_id: UUID, body: InviteMemberRequest, member: GovWriter, db: DB):
    return await CirclesService(db).invite_member(
        circle_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.get("/{circle_id}/health", response_model=CircleHealthSnapshotResponse)
async def circle_health(circle_id: UUID, member: ActiveMember, db: DB):
    return await CirclesService(db).get_circle_health(circle_id, _uuid.UUID(member.org_id))
