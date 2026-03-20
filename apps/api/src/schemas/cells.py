from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

from .common import OrmBase, MemberRef, CircleRef, DormainRef
from ..models.types import (
    CellType, CellState, CellVisibility, ContributionType,
    MotionType, PreValidationStatus,
)


# ── Requests ──────────────────────────────────────────────────────────────────

class AddContributionRequest(BaseModel):
    body: str = Field(..., min_length=1)
    contribution_type: ContributionType = ContributionType.DISCUSSION


class ImportCommonsContextRequest(BaseModel):
    """
    Snapshot-import selected Commons posts into Cell.
    Humans select which posts to import — no automated feed.
    """
    post_ids: list[uuid.UUID] = Field(..., min_length=1, max_length=50)


class CastVoteRequest(BaseModel):
    motion_id: uuid.UUID
    dormain_id: uuid.UUID = Field(
        ...,
        description="Dormain under which this vote is cast. Must be in voter's Circle mandate.",
    )
    vote: str = Field(..., pattern=r"^(yea|nay|abstain)$")


class FileCrystallisedMotionRequest(BaseModel):
    """
    File a motion from the crystallise draft.
    The draft was produced by the Insight Engine on the sponsor's crystallise click.

    non_system and hybrid motions REQUIRE implementing_circle_ids.
    Missing this field on non_system/hybrid raises 422 before any DB write.
    """
    motion_type: MotionType

    # Directive — required for non_system and hybrid
    directive_body: str | None = Field(None, min_length=10)
    directive_commitments: list[str] | None = None
    directive_ambiguities_flagged: list[str] | None = None

    # Specifications — required for sys_bound and hybrid
    specifications: list[MotionSpecificationInput] | None = None

    # Accountability — required for non_system and hybrid
    implementing_circle_ids: list[uuid.UUID] | None = Field(
        None,
        description=(
            "Circles responsible for executing this directive. "
            "REQUIRED for non_system and hybrid motions. "
            "Absent on sys_bound (Integrity Engine executes)."
        ),
    )

    @model_validator(mode="after")
    def validate_by_type(self) -> FileCrystallisedMotionRequest:
        t = self.motion_type

        if t in (MotionType.NON_SYSTEM, MotionType.HYBRID):
            if not self.implementing_circle_ids:
                raise ValueError(
                    "MOTION_MISSING_CIRCLES: implementing_circle_ids is required "
                    f"for {t.value} motions."
                )
            if not self.directive_body:
                raise ValueError(
                    f"directive_body is required for {t.value} motions."
                )

        if t in (MotionType.SYS_BOUND, MotionType.HYBRID):
            if not self.specifications:
                raise ValueError(
                    f"specifications is required for {t.value} motions."
                )

        if t == MotionType.SYS_BOUND and self.implementing_circle_ids:
            raise ValueError(
                "implementing_circle_ids must not be set for sys_bound motions. "
                "Sys-bound motions are executed by the Integrity Engine."
            )

        return self


class MotionSpecificationInput(BaseModel):
    parameter: str = Field(..., max_length=100)
    new_value: dict | str | int | float | bool
    justification: str = Field(..., min_length=20, max_length=5000)


class DissolveCellRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=2000)


# ── Responses ─────────────────────────────────────────────────────────────────

class CellResponse(OrmBase):
    id: uuid.UUID
    org_id: uuid.UUID
    cell_type: CellType
    visibility: CellVisibility
    state: CellState
    initiating_member: MemberRef
    founding_mandate: str | None
    revision_directive: str | None
    invited_circles: list[CircleRef]
    created_at: datetime
    state_changed_at: datetime


class ContributionResponse(OrmBase):
    id: uuid.UUID
    cell_id: uuid.UUID
    author: MemberRef
    body: str
    contribution_type: ContributionType
    commons_post_ref: uuid.UUID | None
    created_at: datetime


class CellMinutesResponse(BaseModel):
    """Rolling minutes produced by the Insight Engine. Updated on each contribution."""
    cell_id: uuid.UUID
    key_positions: list[str]
    open_questions: list[str]
    emerging_consensus: list[str]
    points_of_contention: list[str]
    contribution_count: int
    generated_at: datetime


class VoteSummaryResponse(BaseModel):
    """
    Aggregate vote tally. Individual votes are NOT returned here —
    only the weighted totals. Individual voter identity is visible
    only in the ledger audit archive after the motion is enacted.
    """
    motion_id: uuid.UUID
    dormain_id: uuid.UUID
    dormain_name: str
    yea_weight: float
    nay_weight: float
    abstain_weight: float
    total_weight: float
    yea_count: int
    nay_count: int
    abstain_count: int
    quorum_met: bool
    threshold_met: bool
    closed_at: datetime | None


class CellVoteSummariesResponse(BaseModel):
    motion_id: uuid.UUID
    tallies_by_dormain: list[VoteSummaryResponse]
    overall_result: str | None  # passed | failed | pending


class CrystalliseDraftResponse(BaseModel):
    """
    Motion draft returned by the Insight Engine on crystallise.
    Not persisted until filed. Sponsor edits before confirming.
    """
    draft_id: str
    motion_type_suggested: MotionType
    directive_draft: DirectiveDraft | None
    specification_drafts: list[SpecificationDraft] | None
    accountability_circles_suggested: list[CircleRef] | None
    generated_at: datetime


class DirectiveDraft(BaseModel):
    body: str
    commitments: list[str]
    ambiguities_flagged: list[str]
    contributing_members: list[MemberRef]


class SpecificationDraft(BaseModel):
    parameter: str
    current_value: dict | str | int | float | bool | None
    proposed_value: dict | str | int | float | bool
    justification_draft: str
    pre_validation_status: PreValidationStatus


class FiledMotionResponse(OrmBase):
    id: uuid.UUID
    motion_type: MotionType
    state: str
    cell_id: uuid.UUID
    filed_by: MemberRef
    implementing_circle_ids: list[uuid.UUID] | None
    created_at: datetime


class CompositionProfileResponse(BaseModel):
    cell_id: uuid.UUID
    computed_at: datetime
    dormain_weights: dict[str, float]
    gap_dormains: list[DormainRef]
