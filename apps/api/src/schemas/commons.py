from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field

from .common import OrmBase, MemberRef, DormainRef, Paginated
from ..models.types import TagSource


# ── Requests ──────────────────────────────────────────────────────────────────

class CreateThreadRequest(BaseModel):
    title: str = Field(..., min_length=4, max_length=500)
    body: str = Field(..., min_length=10)
    dormain_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Author dormain signal. Inferential Engine may add or correct.",
    )


class CreatePostRequest(BaseModel):
    body: str = Field(..., min_length=1)
    parent_post_id: uuid.UUID | None = Field(
        None,
        description="Set to create a threaded reply.",
    )


class FormalReviewRequest(BaseModel):
    """
    Circle member formal review of a Commons post.
    Emits formal_review_filed event → Integrity Engine computes ΔC (G=0.5).
    score_s is 0.0–1.0. Centred at 0.5 — below 0.5 is negative signal.
    """
    dormain_id: uuid.UUID = Field(
        ...,
        description="Dormain in which this review is being cast. Must match reviewer's Circle mandate.",
    )
    score_s: float = Field(..., ge=0.0, le=1.0)
    rationale: str | None = Field(None, max_length=2000)


class CorrectDormainTagRequest(BaseModel):
    """
    Human correction of an Inferential Engine dormain tag.
    Removes the specified dormain tag and replaces it with the corrected one.
    """
    remove_dormain_id: uuid.UUID
    add_dormain_id: uuid.UUID
    rationale: str | None = Field(None, max_length=500)


class ConfirmSponsorshipRequest(BaseModel):
    """
    Confirm Cell creation after reviewing the Insight Engine mandate draft.
    Sponsor may edit the draft before confirming.
    """
    founding_mandate: str = Field(
        ..., min_length=50, max_length=10000,
        description="Edited or accepted mandate draft from the sponsor step.",
    )
    invited_circle_ids: list[uuid.UUID] = Field(
        ..., min_length=1,
        description="Circles invited into the deliberation Cell.",
    )


class ThreadFilterParams(BaseModel):
    dormain_id: uuid.UUID | None = None
    state: str | None = None       # open | frozen | sponsored | closed
    search: str | None = Field(None, max_length=200)
    page: int = 1
    page_size: int = 25


# ── Responses ─────────────────────────────────────────────────────────────────

class DormainTagResponse(OrmBase):
    dormain: DormainRef
    source: TagSource
    tagged_by: MemberRef | None
    tagged_at: datetime
    corrected_from: DormainRef | None


class CommonsThreadResponse(OrmBase):
    id: uuid.UUID
    title: str
    body: str
    author: MemberRef
    tags: list[DormainTagResponse]
    state: str
    visibility: str
    sponsored_at: datetime | None
    sponsoring_cell_id: uuid.UUID | None
    post_count: int
    created_at: datetime


class CommonsThreadSummaryResponse(OrmBase):
    """Compact version for list views and feed."""
    id: uuid.UUID
    title: str
    body_preview: str
    author: MemberRef
    tags: list[DormainRef]
    state: str
    post_count: int
    created_at: datetime
    sponsored_at: datetime | None


class CommonsPostResponse(OrmBase):
    id: uuid.UUID
    thread_id: uuid.UUID
    author: MemberRef
    body: str
    parent_post_id: uuid.UUID | None
    formal_review_count: int
    created_at: datetime
    edited_at: datetime | None


class FormalReviewResponse(OrmBase):
    id: uuid.UUID
    post_id: uuid.UUID
    dormain: DormainRef
    score_s: float
    # reviewer_id NOT returned — kept private to protect review independence
    delta_c_event_id: uuid.UUID | None
    reviewed_at: datetime


class SponsorDraftResponse(BaseModel):
    """
    Insight Engine mandate draft returned after sponsor click.
    Not persisted until confirmed via POST /sponsor/confirm.
    """
    draft_id: str  # ephemeral reference, not a DB UUID
    founding_mandate: str
    key_themes: list[str]
    contributing_members: list[MemberRef]
    generated_at: datetime


class SponsorConfirmResponse(OrmBase):
    """Returned after Cell creation is confirmed."""
    cell_id: uuid.UUID
    thread_id: uuid.UUID
    founding_mandate: str
    invited_circles: list["CircleRef"]
    created_at: datetime


# Resolve forward ref
from .common import CircleRef
SponsorConfirmResponse.model_rebuild()
