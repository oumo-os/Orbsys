from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from .common import OrmBase, CircleRef
from ..models.types import STFType, STFState, VerdictType


# ── Requests ──────────────────────────────────────────────────────────────────

class CommissionSTFRequest(BaseModel):
    stf_type: STFType
    mandate: str = Field(..., min_length=20, max_length=10000)
    commissioned_by_circle_id: uuid.UUID
    motion_id: uuid.UUID | None = None
    resolution_id: uuid.UUID | None = None
    subject_member_id: uuid.UUID | None = None
    deadline: datetime | None = None


class EnactResolutionRequest(BaseModel):
    """
    Sys-bound only. Initiates synchronous Integrity Engine atomic write.
    Returns only when the transaction commits or rolls back.
    """
    resolution_id: uuid.UUID
    confirmation: str = Field(
        ..., pattern=r"^ENACT$",
        description='Must be the string "ENACT" — prevents accidental enactment.',
    )


# ── Blind verdict (filed via Blind Review API, not this API) ──────────────────

class FileVerdictRequest(BaseModel):
    """
    Posted to the Blind Review API (/blind/:stf_id/verdicts).
    Not accepted by the main API.
    """
    verdict: VerdictType
    rationale: str | None = Field(None, max_length=10000)
    revision_directive: str | None = Field(
        None, max_length=10000,
        description="Required when verdict is revision_request.",
    )
    checklist: dict | None = None


# ── Responses ─────────────────────────────────────────────────────────────────

class STFInstanceResponse(OrmBase):
    id: uuid.UUID
    org_id: uuid.UUID
    stf_type: STFType
    state: STFState
    mandate: str
    commissioned_by_circle: CircleRef | None
    motion_id: uuid.UUID | None
    resolution_id: uuid.UUID | None
    subject_member_id: uuid.UUID | None  # only populated for non-blind jSTF
    deadline: datetime | None
    assignment_count: int
    verdicts_filed: int
    created_at: datetime
    completed_at: datetime | None


class STFInstanceSummaryResponse(OrmBase):
    id: uuid.UUID
    stf_type: STFType
    state: STFState
    mandate_preview: str   # first 200 chars
    deadline: datetime | None
    assignment_count: int
    verdicts_filed: int
    created_at: datetime


class STFAssignmentResponse(OrmBase):
    """
    Identity policy:
    - xSTF (non-blind): member included
    - All blind types (aSTF, vSTF, jSTF, meta-aSTF): member_id ABSENT

    The schema enforces this — member is None for blind types.
    The service layer is responsible for setting it correctly.
    """
    id: uuid.UUID
    stf_instance_id: uuid.UUID
    stf_type: STFType
    # member is ABSENT (None) for all blind STF types
    member: "MemberRef | None"
    slot_type: str
    assigned_at: datetime
    rotation_end: datetime | None
    verdict_filed_at: datetime | None


BLIND_STF_TYPES = {
    STFType.ASTF_MOTION,
    STFType.ASTF_PERIODIC,
    STFType.VSTF,
    STFType.JSTF,
    STFType.META_ASTF,
}


class VerdictAggregateResponse(BaseModel):
    """
    Aggregated verdict counts. Individual verdicts are NOT returned here.
    reviewer_id is NEVER returned by any endpoint.

    Individual rationales become available after STF completes,
    attributed to slot_type only (not member identity).
    """
    stf_instance_id: uuid.UUID
    stf_type: STFType
    state: STFState
    total_assignments: int
    verdicts_filed: int
    counts: dict[str, int]           # verdict_type → count
    majority_verdict: VerdictType | None
    completed_at: datetime | None


class VerdictRationaleResponse(BaseModel):
    """
    Individual verdict rationale — available only after STF completes.
    Attributed to slot_type, never to member identity.
    """
    assignment_id: uuid.UUID
    slot_type: str                   # "standard" | "novice" | "veteran"
    verdict: VerdictType
    rationale: str | None
    revision_directive: str | None
    filed_at: datetime


class EnactResolutionResponse(BaseModel):
    """
    Synchronous response from Integrity Engine atomic write.
    Returned only when the transaction is fully committed or rolled back.
    """
    resolution_id: uuid.UUID
    resolution_ref: str
    state: str                       # enacted | contested
    gate2_diffs: list["Gate2DiffEntry"]
    enacted_at: datetime | None
    contested_reason: str | None


# ── Unsealing ─────────────────────────────────────────────────────────────────

class UnsealingEventResponse(OrmBase):
    id: uuid.UUID
    stf_instance_id: uuid.UUID
    assignment_id: uuid.UUID
    unsealing_condition: str
    triggered_by_ruling_id: uuid.UUID
    unsealed_at: datetime


# Resolve forward refs
from .common import MemberRef
from .motions import Gate2DiffEntry
STFAssignmentResponse.model_rebuild()
EnactResolutionResponse.model_rebuild()
