from fastapi import APIRouter, Query
from ..core.dependencies import ActiveMember, GovWriter, DB
from ..services.org import OrgService
from ..schemas import (
    CreateOrgRequest, OrgResponse,
    CreateDormainRequest, DormainResponse,
    OrgParameterResponse,
)

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
