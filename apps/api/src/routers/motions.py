import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.motions import MotionsService
from ..schemas import (
    MotionResponse,
    ValidateSpecificationRequest, ValidateSpecificationResponse,
)

router = APIRouter(prefix="/motions", tags=["motions"])


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
