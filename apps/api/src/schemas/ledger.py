from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel

from .common import OrmBase, Paginated


# ── Responses ─────────────────────────────────────────────────────────────────

class LedgerEventResponse(OrmBase):
    id: uuid.UUID
    org_id: uuid.UUID
    event_type: str
    subject_id: uuid.UUID | None
    subject_type: str | None
    payload: dict
    supersedes: uuid.UUID | None
    triggered_by_member: uuid.UUID | None   # member_id — visible (non-blind action)
    triggered_by_resolution: uuid.UUID | None
    created_at: datetime
    prev_hash: str
    event_hash: str


class LedgerVerifyResponse(BaseModel):
    """
    Result of walking the org's full hash chain.
    Available to all active members — this is the transparency guarantee.
    """
    status: str                          # ok | broken
    verified_events: int
    first_broken_event_id: uuid.UUID | None
    verified_at: datetime


class AuditReportResponse(BaseModel):
    """
    Completed STF report from the audit archive.
    Includes verdict rationales attributed to slot_type.
    Reviewer identity is NEVER included.
    """
    stf_instance_id: uuid.UUID
    stf_type: str
    mandate: str
    commissioned_by_circle_id: uuid.UUID | None
    motion_id: uuid.UUID | None
    resolution_id: uuid.UUID | None
    majority_verdict: str
    rationales: list[AuditRationale]
    completed_at: datetime
    ledger_event_id: uuid.UUID


class AuditRationale(BaseModel):
    slot_type: str
    verdict: str
    rationale: str | None
    revision_directive: str | None
