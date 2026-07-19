from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from .common import OrmBase, MemberRef, CircleRef
from ..models.types import (
    MotionType, MotionState, ResolutionState, ImplementationType,
    Gate2Agent, PreValidationStatus,
)


# ── Responses ─────────────────────────────────────────────────────────────────

class MotionDirectiveResponse(OrmBase):
    body: str
    commitments: list[str] | None
    ambiguities_flagged: list[str] | None


class MotionSpecificationResponse(OrmBase):
    id: uuid.UUID
    parameter: str
    new_value: dict
    justification: str
    pre_validation_status: PreValidationStatus
    pre_validated_at: datetime | None


class Gate2DiffEntry(OrmBase):
    parameter: str
    specified_value: dict
    applied_value: dict | None
    match: bool
    checked_at: datetime


class ResolutionResponse(OrmBase):
    id: uuid.UUID
    resolution_ref: str
    state: ResolutionState
    implementation_type: ImplementationType
    gate2_agent: Gate2Agent
    implementing_circles: list[CircleRef] | None
    gate2_diffs: list[Gate2DiffEntry]
    enacted_at: datetime | None
    created_at: datetime


class MotionResponse(OrmBase):
    id: uuid.UUID
    org_id: uuid.UUID
    cell_id: uuid.UUID
    motion_type: MotionType
    state: MotionState
    filed_by: MemberRef
    directive: MotionDirectiveResponse | None
    specifications: list[MotionSpecificationResponse]
    # Non-system / hybrid only
    implementing_circle_ids: list[uuid.UUID] | None
    implementing_circles: list[CircleRef] | None
    resolution: ResolutionResponse | None
    created_at: datetime
    crystallised_at: datetime | None
    state_changed_at: datetime


# ── Specification validation (dry-run) ───────────────────────────────────────

class ValidateSpecificationRequest(BaseModel):
    """
    Dry-run validation for a sys-bound motion specification.
    No event emitted. No state change.
    """
    parameter: str
    new_value: dict | str | int | float | bool
    justification: str = Field(..., min_length=20)


class SpecificationValidationResult(BaseModel):
    parameter: str
    status: PreValidationStatus
    current_value: dict | str | int | float | bool | None
    proposed_value: dict | str | int | float | bool
    validation_message: str | None
    valid_range: str | None  # human-readable range description


class ValidateSpecificationResponse(BaseModel):
    """All specification items validated in a single call."""
    motion_id: uuid.UUID
    results: list[SpecificationValidationResult]
    all_valid: bool
