import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, Query
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.motions import MotionsService
from ..schemas import (
    MotionResponse,
    ValidateSpecificationRequest, ValidateSpecificationResponse,
    Paginated,
)

router = APIRouter(prefix="/motions", tags=["motions"])


@router.get("", response_model=Paginated[MotionResponse])
async def list_motions(
    member: ActiveMember, db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    state: str | None = Query(None, description="Filter by motion state"),
    cell_id: _uuid.UUID | None = Query(None, description="Filter by cell"),
):
    return await MotionsService(db).list_motions(
        _uuid.UUID(member.org_id), page, page_size, state, cell_id
    )


@router.get("/{motion_id}", response_model=MotionResponse)
async def get_motion(motion_id: UUID, member: ActiveMember, db: DB):
    return await MotionsService(db).get_motion(motion_id, _uuid.UUID(member.org_id))


@router.post("/{motion_id}/validate-specification", response_model=ValidateSpecificationResponse)
async def validate_specification(
    motion_id: UUID, body: ValidateSpecificationRequest, member: GovWriter, db: DB,
):
    return await MotionsService(db).validate_specification(
        motion_id, _uuid.UUID(member.org_id), body
    )
