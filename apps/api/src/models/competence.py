import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base
from .types import uuid_pk, created_at_col, updated_at_col, ActivityType, McmpStatus, CredentialType


class CompetenceScore(Base):
    """Materialised W_s / W_h per member per dormain. Written ONLY by Integrity Engine."""
    __tablename__ = "competence_scores"
    __table_args__ = (UniqueConstraint("member_id", "dormain_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    w_s: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    w_s_peak: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    w_h: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    volatility_k: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=60)
    proof_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    mcmp_status: Mapped[McmpStatus] = mapped_column(String(10), nullable=False, default=McmpStatus.ACTIVE)
    updated_at: Mapped[datetime] = updated_at_col()

    member: Mapped["Member"] = relationship(back_populates="competence_scores")  # type: ignore[name-defined]
    dormain: Mapped["Dormain"] = relationship(back_populates="competence_scores")  # type: ignore[name-defined]


class Curiosity(Base):
    """Self-declared member interest. Zero governance weight — Inferential Engine only."""
    __tablename__ = "curiosities"
    __table_args__ = (UniqueConstraint("member_id", "dormain_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    signal: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)  # 0.000–1.000
    declared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = updated_at_col()

    member: Mapped["Member"] = relationship(back_populates="curiosities")  # type: ignore[name-defined]


class DeltaCEvent(Base):
    """Append-only. Every ΔC computation. Written ONLY by Integrity Engine."""
    __tablename__ = "delta_c_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    activity_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    activity_type: Mapped[ActivityType] = mapped_column(String(40), nullable=False)
    gravity_g: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    volatility_k: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    delta_raw: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    delta_applied: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    ws_before: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    ws_after: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    # applied | pending_audit | superseded
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="applied")
    superseded_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("delta_c_events.id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeltaCReviewer(Base):
    """
    Reviewer set R for each ΔC event. Append-only.
    NOT exposed via application API — integrity_rw role only.
    reviewer_id queryable only by Integrity Engine.
    """
    __tablename__ = "delta_c_reviewers"

    id: Mapped[uuid.UUID] = uuid_pk()
    delta_c_event_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("delta_c_events.id"), nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    score_s: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    reviewer_w_d: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    circle_multiplier_m: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)  # 1.00 | 1.20 | 1.60
    provenance_note: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WhCredential(Base):
    """Hard Competence credential. Verified by vSTF → aSTF gate."""
    __tablename__ = "wh_credentials"

    id: Mapped[uuid.UUID] = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    credential_type: Mapped[CredentialType] = mapped_column(String(40), nullable=False)
    value_wh: Mapped[float] = mapped_column(Numeric(7, 2), nullable=False)
    vdc_reference: Mapped[Optional[str]] = mapped_column(String(500))
    vstf_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    resolution_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # wh_preliminary | wh_verified
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="wh_preliminary")
