from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from .common import OrmBase, MemberRef, DormainRef
from ..models.types import CredentialType, McmpStatus, PreValidationStatus


# ── Requests ──────────────────────────────────────────────────────────────────

class SubmitWhClaimRequest(BaseModel):
    """
    Submit a Hard Competence credential for vSTF verification.
    vdc_reference should point to a verifiable external document.
    """
    dormain_id: uuid.UUID
    credential_type: CredentialType
    claimed_value_wh: float = Field(..., ge=0.0, le=10000.0)
    vdc_reference: str = Field(
        ..., max_length=500,
        description="URL or document reference to the verifiable credential.",
    )
    justification: str = Field(..., min_length=50, max_length=5000)


# ── Responses ─────────────────────────────────────────────────────────────────

class CompetenceScoreResponse(OrmBase):
    dormain_id: uuid.UUID
    dormain_name: str
    w_s: float
    w_s_peak: float
    w_h: float
    volatility_k: int
    proof_count: int
    last_activity_at: datetime | None
    mcmp_status: McmpStatus
    updated_at: datetime


class CompetenceScoresResponse(BaseModel):
    """All competence scores for the current member."""
    member_id: uuid.UUID
    scores: list[CompetenceScoreResponse]


class LeaderboardEntryResponse(OrmBase):
    rank: int
    member: MemberRef
    w_s: float
    w_s_peak: float
    last_activity_at: datetime | None


class DormainLeaderboardResponse(BaseModel):
    dormain: DormainRef
    entries: list[LeaderboardEntryResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class WhClaimResponse(OrmBase):
    id: uuid.UUID
    dormain_id: uuid.UUID
    dormain_name: str
    credential_type: CredentialType
    claimed_value_wh: float
    vdc_reference: str | None
    status: str  # wh_preliminary | wh_verified
    vstf_id: uuid.UUID | None
    verified_at: datetime
    expires_at: datetime | None


class DormainListResponse(OrmBase):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    decay_fn: str
    decay_half_life_months: float
    decay_floor_pct: float
    created_at: datetime


# ── ΔC event (read-only, for ledger transparency) ────────────────────────────

class DeltaCEventResponse(OrmBase):
    """
    Public view of a ΔC event. Reviewer identities are NOT included —
    those live in delta_c_reviewers, accessible only to the Integrity Engine.
    """
    id: uuid.UUID
    dormain_id: uuid.UUID
    dormain_name: str
    activity_type: str
    gravity_g: float
    delta_applied: float
    ws_before: float
    ws_after: float
    status: str
    computed_at: datetime
