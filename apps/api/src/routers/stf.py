import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, Query
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.stf import STFService
from ..schemas import (
    CommissionSTFRequest, STFInstanceResponse, STFInstanceSummaryResponse,
    STFAssignmentResponse, VerdictAggregateResponse, VerdictRationaleResponse,
    EnactResolutionRequest, EnactResolutionResponse,
    Paginated,
)

router = APIRouter(prefix="/stf", tags=["stf"])


@router.get("", response_model=Paginated[STFInstanceSummaryResponse])
async def list_stf_instances(
    member: ActiveMember, db: DB,
    stf_type: str | None = Query(None),
    state: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    return await STFService(db).list_stf_instances(
        _uuid.UUID(member.org_id), stf_type, state, page, page_size
    )


@router.post("", response_model=STFInstanceResponse, status_code=201)
async def commission_stf(body: CommissionSTFRequest, member: GovWriter, db: DB):
    return await STFService(db).commission_stf(
        _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.get("/{stf_id}", response_model=STFInstanceResponse)
async def get_stf(stf_id: UUID, member: ActiveMember, db: DB):
    return await STFService(db).get_stf(stf_id, _uuid.UUID(member.org_id))


@router.get("/{stf_id}/assignments", response_model=list[STFAssignmentResponse])
async def get_assignments(stf_id: UUID, member: ActiveMember, db: DB):
    return await STFService(db).get_assignments(stf_id, _uuid.UUID(member.org_id))


@router.get("/{stf_id}/verdicts", response_model=VerdictAggregateResponse)
async def get_verdicts(stf_id: UUID, member: ActiveMember, db: DB):
    return await STFService(db).get_verdicts(stf_id, _uuid.UUID(member.org_id))


@router.get("/{stf_id}/verdicts/rationales", response_model=list[VerdictRationaleResponse])
async def get_verdict_rationales(stf_id: UUID, member: ActiveMember, db: DB):
    return await STFService(db).get_verdict_rationales(stf_id, _uuid.UUID(member.org_id))


@router.post("/{stf_id}/resolutions", response_model=EnactResolutionResponse, status_code=201)
async def enact_resolution(stf_id: UUID, body: EnactResolutionRequest, member: GovWriter, db: DB):
    return await STFService(db).enact_resolution(
        stf_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )
