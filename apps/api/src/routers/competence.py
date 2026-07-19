import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, Query
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.competence import CompetenceService
from ..schemas import (
    DormainListResponse, DormainLeaderboardResponse,
    CompetenceScoresResponse, SubmitWhClaimRequest,
    WhClaimResponse,
)

router = APIRouter(prefix="/competence", tags=["competence"])


@router.get("/dormains", response_model=list[DormainListResponse])
async def list_dormains(member: ActiveMember, db: DB):
    return await CompetenceService(db).list_dormains(_uuid.UUID(member.org_id))


@router.get("/leaderboard/{dormain_id}", response_model=DormainLeaderboardResponse)
async def dormain_leaderboard(
    dormain_id: UUID, member: ActiveMember, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    return await CompetenceService(db).dormain_leaderboard(
        dormain_id, _uuid.UUID(member.org_id), page, page_size
    )


@router.get("/scores/me", response_model=CompetenceScoresResponse)
async def my_scores(member: ActiveMember, db: DB):
    return await CompetenceService(db).my_scores(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id)
    )


@router.post("/wh-claims", response_model=WhClaimResponse, status_code=201)
async def submit_wh_claim(body: SubmitWhClaimRequest, member: GovWriter, db: DB):
    return await CompetenceService(db).submit_wh_claim(
        _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.get("/wh-claims/me", response_model=list[WhClaimResponse])
async def my_wh_claims(member: ActiveMember, db: DB):
    return await CompetenceService(db).my_wh_claims(
        _uuid.UUID(member.member_id), _uuid.UUID(member.org_id)
    )
