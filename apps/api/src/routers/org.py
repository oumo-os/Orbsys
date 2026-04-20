import uuid
from pydantic import BaseModel
from fastapi import APIRouter, Query
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.org import OrgService
from ..schemas import (
    CreateOrgRequest, OrgResponse,
    CreateDormainRequest, DormainResponse,
    OrgParameterResponse,
)
from ..schemas.circles import CircleResponse
from ..schemas.common import DormainRef

router = APIRouter(prefix="/org", tags=["org"])


@router.post("", response_model=OrgResponse, status_code=201)
async def create_org(body: CreateOrgRequest, db: DB):
    """Bootstrap step 1 — org creation. No auth required."""
    return await OrgService(db).create_org(body)


@router.get("", response_model=OrgResponse)
async def get_org(member: ActiveMember, db: DB):
    import uuid
    return await OrgService(db).get_org(uuid.UUID(member.org_id))


@router.get("/parameters", response_model=list[OrgParameterResponse])
async def get_parameters(member: ActiveMember, db: DB):
    import uuid
    return await OrgService(db).get_parameters(uuid.UUID(member.org_id))


@router.get("/dormains", response_model=list[DormainResponse])
async def list_dormains(member: ActiveMember, db: DB):
    import uuid
    return await OrgService(db).list_dormains(uuid.UUID(member.org_id))


@router.post("/dormains", response_model=DormainResponse, status_code=201)
async def create_dormain(body: CreateDormainRequest, member: GovWriter, db: DB):
    """Bootstrap step 2 — provisional dormain definition."""
    import uuid
    return await OrgService(db).create_dormain(
        uuid.UUID(member.org_id), body, uuid.UUID(member.member_id)
    )


class BootstrapCompleteRequest(BaseModel):
    membership_policy: str = "open_application"
    """
    Governs how new members join after bootstrap:
      open_application — anyone can apply, Membership Circle reviews
      invite_only      — must be invited by an existing Circle member
      closed           — org is frozen, no new members
    """


class BootstrapCircleRequest(BaseModel):
    name: str
    description: str | None = None
    dormain_ids: list[uuid.UUID] = []


@router.post("/bootstrap-complete", response_model=OrgResponse)
async def bootstrap_complete(
    body: BootstrapCompleteRequest,
    member: GovWriter,
    db: DB,
):
    """
    Complete the founding bootstrap — sets bootstrapped_at, dissolves
    founding circles, seeds membership_policy.

    Call this once the founding deliberation is done. After this:
      - POST /auth/register returns 403
      - POST /members/apply is the join path (if policy allows)
      - Circle invitations require a vote, not auto-confirm

    Idempotent-safe: returns 403 ALREADY_BOOTSTRAPPED if already live.
    """
    import uuid
    return await OrgService(db).bootstrap_complete(
        uuid.UUID(member.org_id),
        uuid.UUID(member.member_id),
        body.membership_policy,
    )


@router.post("/circles", response_model=CircleResponse, status_code=201)
async def create_circle_bootstrap(body: BootstrapCircleRequest, member: GovWriter, db: DB):
    """
    Bootstrap step 3b — direct Circle creation.
    Only permitted while org.bootstrapped_at is null (bootstrap window open).
    In live operation, Circles are created via governance motions.
    """
    import uuid
    return await OrgService(db).create_circle_bootstrap(
        uuid.UUID(member.org_id), uuid.UUID(member.member_id), body
    )
