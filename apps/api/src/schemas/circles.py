from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from .common import OrmBase, MemberRef, DormainRef
from ..models.types import MemberState, MandateType


# ── Requests ──────────────────────────────────────────────────────────────────

class InviteMemberRequest(BaseModel):
    member_id: uuid.UUID
    justification: str = Field(
        ..., min_length=20, max_length=2000,
        description="Reason for invitation, visible to Circle members voting on it.",
    )


# ── Responses ─────────────────────────────────────────────────────────────────

class CircleDormainResponse(OrmBase):
    dormain: DormainRef
    mandate_type: MandateType
    added_at: datetime
    removed_at: datetime | None


class CircleMemberResponse(OrmBase):
    member: MemberRef
    joined_at: datetime
    current_state: MemberState
    # W_s in this Circle's primary Dormain — context for the invitation view
    primary_dormain_ws: float | None


class CircleResponse(OrmBase):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    tenets: str | None
    founding_circle: bool
    dormains: list[CircleDormainResponse]
    member_count: int
    created_at: datetime
    dissolved_at: datetime | None


class CircleSummaryResponse(OrmBase):
    """Compact form for lists and embedded refs."""
    id: uuid.UUID
    name: str
    description: str | None
    dormains: list[DormainRef]
    member_count: int
    dissolved_at: datetime | None


class CircleHealthSnapshotResponse(BaseModel):
    """
    Latest Circle health data from the most recent periodic aSTF.
    Populated after first periodic audit — null before that.
    """
    circle_id: uuid.UUID
    circle_name: str
    snapshot_at: datetime | None
    overall_verdict: str | None  # clear | concerns | violation
    active_member_count: int
    median_ws_primary_dormain: float | None
    participation_rate_90d: float | None
    open_concerns: list[str]
    stf_instance_id: uuid.UUID | None


class InvitationResponse(BaseModel):
    """Returned after a member invitation is submitted."""
    invitation_id: uuid.UUID
    circle_id: uuid.UUID
    invited_member: MemberRef
    status: str  # pending_vote | accepted | rejected
    created_at: datetime
