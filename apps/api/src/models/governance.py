import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base
from .types import (
    uuid_pk, created_at_col,
    CellType, CellState, CellVisibility, ContributionType, TagSource, FreezeReason,
    MotionType, MotionState, ResolutionState, ImplementationType, Gate2Agent,
    STFType, STFState, VerdictType, UnsealingCondition, PreValidationStatus,
)


# ── Commons ───────────────────────────────────────────────────────────────────

class CommonsThread(Base):
    __tablename__ = "commons_threads"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="inherited")
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    freeze_reason: Mapped[Optional[FreezeReason]] = mapped_column(String(20))
    freeze_ref: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    sponsored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    sponsoring_cell_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = created_at_col()

    tags: Mapped[list["CommonsThreadDormainTag"]] = relationship(back_populates="thread")
    posts: Mapped[list["CommonsPost"]] = relationship(back_populates="thread")


class CommonsThreadDormainTag(Base):
    __tablename__ = "commons_thread_dormain_tags"
    __table_args__ = (UniqueConstraint("thread_id", "dormain_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    thread_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("commons_threads.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    source: Mapped[TagSource] = mapped_column(String(30), nullable=False)
    tagged_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"))
    tagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    corrected_from_dormain_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"))

    thread: Mapped["CommonsThread"] = relationship(back_populates="tags")


class CommonsPost(Base):
    """Append-only. Edits create new rows with edited_at set."""
    __tablename__ = "commons_posts"

    id: Mapped[uuid.UUID] = uuid_pk()
    thread_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("commons_threads.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    parent_post_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("commons_posts.id"))
    created_at: Mapped[datetime] = created_at_col()
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    thread: Mapped["CommonsThread"] = relationship(back_populates="posts")
    formal_reviews: Mapped[list["CommonsFormalReview"]] = relationship(back_populates="post")


class CommonsFormalReview(Base):
    """Circle member formal review of a Commons post. Triggers ΔC (G=0.5)."""
    __tablename__ = "commons_formal_reviews"
    __table_args__ = (UniqueConstraint("post_id", "reviewer_id", "dormain_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    post_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("commons_posts.id"), nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    score_s: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    delta_c_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("delta_c_events.id"))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    post: Mapped["CommonsPost"] = relationship(back_populates="formal_reviews")


# ── Cells ─────────────────────────────────────────────────────────────────────

class Cell(Base):
    __tablename__ = "cells"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    cell_type: Mapped[CellType] = mapped_column(String(30), nullable=False)
    visibility: Mapped[CellVisibility] = mapped_column(String(10), nullable=False, default=CellVisibility.CLOSED)
    state: Mapped[CellState] = mapped_column(String(25), nullable=False, default=CellState.ACTIVE)
    initiating_member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    parent_cell_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cells.id"))
    commons_thread_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("commons_threads.id"))
    commons_snapshot_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    stf_instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    founding_mandate: Mapped[Optional[str]] = mapped_column(Text)
    revision_directive: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()
    state_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    invited_circles: Mapped[list["CellInvitedCircle"]] = relationship(back_populates="cell")
    contributions: Mapped[list["CellContribution"]] = relationship(back_populates="cell")
    composition_profiles: Mapped[list["CellCompositionProfile"]] = relationship(back_populates="cell")
    votes: Mapped[list["CellVote"]] = relationship(back_populates="cell")
    motions: Mapped[list["Motion"]] = relationship(back_populates="cell")


class CellInvitedCircle(Base):
    __tablename__ = "cell_invited_circles"
    __table_args__ = (UniqueConstraint("cell_id", "circle_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    cell_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cells.id"), nullable=False)
    circle_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("circles.id"), nullable=False)
    invited_because: Mapped[str] = mapped_column(String(30), nullable=False)
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cell: Mapped["Cell"] = relationship(back_populates="invited_circles")


class CellContribution(Base):
    """Append-only."""
    __tablename__ = "cell_contributions"

    id: Mapped[uuid.UUID] = uuid_pk()
    cell_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cells.id"), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    contribution_type: Mapped[ContributionType] = mapped_column(String(30), nullable=False, default=ContributionType.DISCUSSION)
    commons_post_ref: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("commons_posts.id"))
    created_at: Mapped[datetime] = created_at_col()

    cell: Mapped["Cell"] = relationship(back_populates="contributions")


class CellCompositionProfile(Base):
    __tablename__ = "cell_composition_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    cell_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cells.id"), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    profile: Mapped[Any] = mapped_column(JSONB, nullable=False)

    cell: Mapped["Cell"] = relationship(back_populates="composition_profiles")


class CellVote(Base):
    """Append-only. Competence-weighted."""
    __tablename__ = "cell_votes"
    __table_args__ = (UniqueConstraint("motion_id", "voter_id", "dormain_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    cell_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cells.id"), nullable=False)
    motion_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("motions.id"), nullable=False)
    voter_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    vote: Mapped[str] = mapped_column(String(10), nullable=False)  # yea | nay | abstain
    w_s_at_vote: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(9, 2), nullable=False)
    voted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cell: Mapped["Cell"] = relationship(back_populates="votes")


# ── Motions & Resolutions ─────────────────────────────────────────────────────

class Motion(Base):
    __tablename__ = "motions"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    cell_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cells.id"), nullable=False)
    motion_type: Mapped[MotionType] = mapped_column(String(15), nullable=False)
    state: Mapped[MotionState] = mapped_column(String(30), nullable=False, default=MotionState.DRAFT)
    filed_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    insight_draft_ref: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = created_at_col()
    crystallised_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    state_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    cell: Mapped["Cell"] = relationship(back_populates="motions")
    directive: Mapped[Optional["MotionDirective"]] = relationship(back_populates="motion", uselist=False)
    specifications: Mapped[list["MotionSpecification"]] = relationship(back_populates="motion")
    resolution: Mapped[Optional["Resolution"]] = relationship(back_populates="motion", uselist=False)


class MotionDirective(Base):
    """Non-system and hybrid motions only."""
    __tablename__ = "motion_directives"

    id: Mapped[uuid.UUID] = uuid_pk()
    motion_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("motions.id"), unique=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    commitments: Mapped[Optional[list]] = mapped_column(ARRAY(Text))
    ambiguities_flagged: Mapped[Optional[list]] = mapped_column(ARRAY(Text))

    motion: Mapped["Motion"] = relationship(back_populates="directive")


class MotionSpecification(Base):
    """Sys-bound and hybrid motions only."""
    __tablename__ = "motion_specifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    motion_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("motions.id"), nullable=False)
    parameter: Mapped[str] = mapped_column(String(100), nullable=False)
    new_value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    pre_validation_status: Mapped[PreValidationStatus] = mapped_column(
        String(30), nullable=False, default=PreValidationStatus.PENDING
    )
    pre_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    motion: Mapped["Motion"] = relationship(back_populates="specifications")


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[uuid.UUID] = uuid_pk()
    motion_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("motions.id"), unique=True, nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    resolution_ref: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    state: Mapped[ResolutionState] = mapped_column(String(30), nullable=False, default=ResolutionState.PENDING_IMPLEMENTATION)
    implementation_type: Mapped[ImplementationType] = mapped_column(String(30), nullable=False)
    # Non-system / hybrid: required — NOT NULL enforced at service layer for these types
    implementing_circle_ids: Mapped[Optional[list]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)))
    gate2_agent: Mapped[Gate2Agent] = mapped_column(String(20), nullable=False)
    enacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()

    motion: Mapped["Motion"] = relationship(back_populates="resolution")
    gate2_diffs: Mapped[list["ResolutionGate2Diff"]] = relationship(back_populates="resolution")


class ResolutionGate2Diff(Base):
    __tablename__ = "resolution_gate2_diffs"

    id: Mapped[uuid.UUID] = uuid_pk()
    resolution_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("resolutions.id"), nullable=False)
    parameter: Mapped[str] = mapped_column(String(100), nullable=False)
    specified_value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    applied_value: Mapped[Optional[dict]] = mapped_column(JSONB)
    match: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    resolution: Mapped["Resolution"] = relationship(back_populates="gate2_diffs")


# ── STF ───────────────────────────────────────────────────────────────────────

class STFInstance(Base):
    __tablename__ = "stf_instances"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    stf_type: Mapped[STFType] = mapped_column(String(20), nullable=False)
    state: Mapped[STFState] = mapped_column(String(15), nullable=False, default=STFState.FORMING)
    mandate: Mapped[str] = mapped_column(Text, nullable=False)
    commissioned_by_circle_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("circles.id"))
    parent_stf_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stf_instances.id"))
    motion_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("motions.id"))
    resolution_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("resolutions.id"))
    subject_member_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"))
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    assignments: Mapped[list["STFAssignment"]] = relationship(back_populates="stf_instance")
    verdicts: Mapped[list["STFVerdict"]] = relationship(back_populates="stf_instance")


class STFAssignment(Base):
    __tablename__ = "stf_assignments"

    id: Mapped[uuid.UUID] = uuid_pk()
    stf_instance_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stf_instances.id"), nullable=False)
    # member_id SEALED for blind types — orbsys_app cannot read this column on blind STFs
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    slot_type: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotation_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    isolated_view_token: Mapped[Optional[str]] = mapped_column(String(500), unique=True)
    verdict_filed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    stf_instance: Mapped["STFInstance"] = relationship(back_populates="assignments")


class STFVerdict(Base):
    """
    Append-only. No reviewer_id column — identity is in STFAssignment.member_id only.
    Identity sealed structurally, not via permissions on a column that exists.
    """
    __tablename__ = "stf_verdicts"

    id: Mapped[uuid.UUID] = uuid_pk()
    stf_instance_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stf_instances.id"), nullable=False)
    assignment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stf_assignments.id"), unique=True, nullable=False)
    verdict: Mapped[VerdictType] = mapped_column(String(30), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    revision_directive: Mapped[Optional[str]] = mapped_column(Text)
    checklist: Mapped[Optional[dict]] = mapped_column(JSONB)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    stf_instance: Mapped["STFInstance"] = relationship(back_populates="verdicts")


class STFUnsealingEvent(Base):
    """Created ONLY on malpractice_finding or judicial_penalty. Append-only."""
    __tablename__ = "stf_unsealing_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    stf_instance_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stf_instances.id"), nullable=False)
    assignment_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("stf_assignments.id"), nullable=False)
    unsealing_condition: Mapped[UnsealingCondition] = mapped_column(String(30), nullable=False)
    triggered_by_ruling_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    unsealed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ── Ledger ────────────────────────────────────────────────────────────────────

class LedgerEvent(Base):
    """
    Append-only. Cryptographic hash chain.
    event_hash = SHA-256(event_id || payload_json || prev_hash)
    Written ONLY by Integrity Engine.
    """
    __tablename__ = "ledger_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    subject_type: Mapped[Optional[str]] = mapped_column(String(50))
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    supersedes: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ledger_events.id"))
    triggered_by_member: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"))
    triggered_by_resolution: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = created_at_col()
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class Notification(Base):
    """
    Written by Insight Engine (via Integrity Engine event).
    Priority tiers: p1 (always), p2 (capped 12/day 3/hr), p3 (digest only).
    """
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    priority: Mapped[str] = mapped_column(String(3), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(60), nullable=False)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    subject_type: Mapped[Optional[str]] = mapped_column(String(50))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[Optional[str]] = mapped_column(String(500))
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class FeedScore(Base):
    """
    Relevance of a Commons thread for a specific member.
    Written by Inferential Engine. Most recent score is authoritative.
    """
    __tablename__ = "feed_scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    thread_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("commons_threads.id"), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    score_basis: Mapped[str] = mapped_column(String(20), nullable=False, default="mandate")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
