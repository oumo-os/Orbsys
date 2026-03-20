import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, Query, status
from fastapi.responses import Response
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.cells import CellsService
from ..schemas import (
    CellResponse, ContributionResponse, AddContributionRequest,
    ImportCommonsContextRequest, CellMinutesResponse,
    CastVoteRequest, CellVoteSummariesResponse,
    CrystalliseDraftResponse,
    FileCrystallisedMotionRequest, FiledMotionResponse,
    CompositionProfileResponse, DissolveCellRequest,
    Paginated,
)

router = APIRouter(prefix="/cells", tags=["cells"])


@router.get("/{cell_id}", response_model=CellResponse)
async def get_cell(cell_id: UUID, member: ActiveMember, db: DB):
    return await CellsService(db).get_cell(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id)
    )


@router.get("/{cell_id}/contributions", response_model=Paginated[ContributionResponse])
async def list_contributions(
    cell_id: UUID, member: ActiveMember, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return await CellsService(db).list_contributions(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), page, page_size
    )


@router.post("/{cell_id}/contributions", response_model=ContributionResponse, status_code=201)
async def add_contribution(cell_id: UUID, body: AddContributionRequest, member: GovWriter, db: DB):
    return await CellsService(db).add_contribution(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.post("/{cell_id}/import-commons-context", response_model=list[ContributionResponse])
async def import_commons_context(
    cell_id: UUID, body: ImportCommonsContextRequest, member: GovWriter, db: DB,
):
    return await CellsService(db).import_commons_context(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.get("/{cell_id}/minutes", response_model=CellMinutesResponse)
async def get_minutes(cell_id: UUID, member: ActiveMember, db: DB):
    return await CellsService(db).get_minutes(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id)
    )


@router.get("/{cell_id}/votes", response_model=CellVoteSummariesResponse)
async def get_votes(cell_id: UUID, member: ActiveMember, db: DB):
    return await CellsService(db).get_votes(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id)
    )


@router.post("/{cell_id}/votes", status_code=204)
async def cast_vote(cell_id: UUID, body: CastVoteRequest, member: GovWriter, db: DB):
    await CellsService(db).cast_vote(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )
    return Response(status_code=204)


@router.post("/{cell_id}/crystallise", response_model=CrystalliseDraftResponse)
async def crystallise(cell_id: UUID, member: GovWriter, db: DB):
    return await CellsService(db).crystallise(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id)
    )


@router.post("/{cell_id}/file-motion", response_model=FiledMotionResponse, status_code=201)
async def file_motion(
    cell_id: UUID, body: FileCrystallisedMotionRequest, member: GovWriter, db: DB,
):
    return await CellsService(db).file_motion(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )


@router.get("/{cell_id}/composition-profile", response_model=CompositionProfileResponse)
async def get_composition_profile(cell_id: UUID, member: ActiveMember, db: DB):
    return await CellsService(db).get_composition_profile(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id)
    )


@router.post("/{cell_id}/dissolve", status_code=204)
async def dissolve_cell(cell_id: UUID, body: DissolveCellRequest, member: GovWriter, db: DB):
    await CellsService(db).dissolve_cell(
        cell_id, _uuid.UUID(member.org_id), _uuid.UUID(member.member_id), body
    )
    return Response(status_code=204)
