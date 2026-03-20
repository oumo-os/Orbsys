import uuid as _uuid
from uuid import UUID
from fastapi import APIRouter, Query
from ..core.dependencies import ActiveMember, DB
from ..services.ledger import LedgerService
from ..schemas import (
    LedgerEventResponse, LedgerVerifyResponse,
    AuditReportResponse, Paginated,
)

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("", response_model=Paginated[LedgerEventResponse])
async def list_events(
    member: ActiveMember, db: DB,
    event_type: str | None = Query(None),
    subject_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return await LedgerService(db).list_events(
        _uuid.UUID(member.org_id), event_type, subject_id, page, page_size
    )


@router.get("/verify", response_model=LedgerVerifyResponse)
async def verify_chain(member: ActiveMember, db: DB):
    return await LedgerService(db).verify_chain(_uuid.UUID(member.org_id))


@router.get("/audit-archive", response_model=Paginated[AuditReportResponse])
async def audit_archive(
    member: ActiveMember, db: DB,
    stf_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    return await LedgerService(db).audit_archive(
        _uuid.UUID(member.org_id), stf_type, page, page_size
    )


@router.get("/{event_id}", response_model=LedgerEventResponse)
async def get_event(event_id: UUID, member: ActiveMember, db: DB):
    return await LedgerService(db).get_event(event_id, _uuid.UUID(member.org_id))
