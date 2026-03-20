from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from .common import OrmBase, DormainRef
from ..models.types import MemberState


# ── Requests ──────────────────────────────────────────────────────────────────

class UpdateMemberRequest(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=255)
    email: str | None = None  # EmailStr — validated at service layer to avoid import cycle


class SetCuriositiesRequest(BaseModel):
    """
    Replaces the full curiosity vector. Keys are dormain_ids (str UUIDs).
    Values are signal strength 0.0–1.0.
    Missing dormains are removed. Extra dormains not in org are rejected.
    """
    curiosities: dict[str, float] = Field(
        ...,
        description="dormain_id → signal strength (0.0–1.0)",
    )

    @field_validator("curiosities")
    @classmethod
    def validate_signals(cls, v: dict) -> dict:
        for dormain_id, signal in v.items():
            if not (0.0 <= signal <= 1.0):
                raise ValueError(f"Signal for {dormain_id} must be 0.0–1.0, got {signal}")
        return v


# ── Responses ─────────────────────────────────────────────────────────────────

class MemberResponse(OrmBase):
    """Full member profile — returned from /members/me and /members/:id."""
    id: uuid.UUID
    handle: str
    display_name: str
    org_id: uuid.UUID
    current_state: MemberState
    joined_at: datetime
    # email only included in /members/me, not /members/:id
    email: str | None = None


class CompetenceScoreSummary(OrmBase):
    dormain_id: uuid.UUID
    dormain_name: str
    w_s: float
    w_s_peak: float
    w_h: float
    volatility_k: int
    last_activity_at: datetime | None


class MemberDetailResponse(MemberResponse):
    """Extended profile — includes competence scores and circle memberships."""
    competence_scores: list[CompetenceScoreSummary] = []
    circle_memberships: list[CircleMembershipSummary] = []


class CircleMembershipSummary(OrmBase):
    circle_id: uuid.UUID
    circle_name: str
    joined_at: datetime
    current_state: MemberState


class CuriosityResponse(OrmBase):
    dormain_id: uuid.UUID
    dormain_name: str
    signal: float
    declared_at: datetime
    updated_at: datetime


# ── Feed ──────────────────────────────────────────────────────────────────────

class FeedItemResponse(OrmBase):
    """
    Relevance-ranked Commons thread for the member's feed.
    feed_relevance = max(mandate_match, curiosity_match).
    """
    thread_id: uuid.UUID
    title: str
    body_preview: str  # first 280 chars
    author: "MemberRef"
    dormain_tags: list[DormainRef]
    state: str
    post_count: int
    created_at: datetime
    sponsored_at: datetime | None
    feed_relevance: float
    relevance_source: str  # "mandate" | "curiosity" | "both"


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationResponse(OrmBase):
    id: uuid.UUID
    priority: str  # p1 | p2 | p3
    notification_type: str
    subject_id: uuid.UUID | None = None
    subject_type: str | None = None
    body: str
    action_url: str | None = None
    read: bool
    created_at: datetime


# Resolve forward refs
from .common import MemberRef
MemberDetailResponse.model_rebuild()
FeedItemResponse.model_rebuild()
