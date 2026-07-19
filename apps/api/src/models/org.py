import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..core.database import Base
from .types import uuid_pk, created_at_col, updated_at_col, MemberState, ExitReason, DecayFn


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    founding_tenets: Mapped[Optional[str]] = mapped_column(Text)
    commons_visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="members_only")
    bootstrapped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()

    members: Mapped[list["Member"]] = relationship(back_populates="org")
    circles: Mapped[list["Circle"]] = relationship(back_populates="org")
    dormains: Mapped[list["Dormain"]] = relationship(back_populates="org")


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (UniqueConstraint("org_id", "handle"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    handle: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    platform_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=True
    )
    display_name_org: Mapped[Optional[str]] = mapped_column(String(300))
    platform_account: Mapped[Optional["PlatformAccount"]] = relationship(back_populates="org_memberships")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_state: Mapped[MemberState] = mapped_column(String(20), nullable=False, default=MemberState.PROBATIONARY)
    proof_of_personhood_ref: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    org: Mapped["Org"] = relationship(back_populates="members")
    circle_memberships: Mapped[list["CircleMember"]] = relationship(back_populates="member")
    competence_scores: Mapped[list["CompetenceScore"]] = relationship(back_populates="member")  # type: ignore[name-defined]
    curiosities: Mapped[list["Curiosity"]] = relationship(back_populates="member")  # type: ignore[name-defined]


class MemberExitRecord(Base):
    __tablename__ = "member_exit_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    circle_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("circles.id"))
    exit_reason: Mapped[ExitReason] = mapped_column(String(40), nullable=False)
    exited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trigger_ref: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    destination_circle_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("circles.id"))


class Dormain(Base):
    __tablename__ = "dormains"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"))
    decay_fn: Mapped[DecayFn] = mapped_column(String(20), nullable=False, default=DecayFn.EXPONENTIAL)
    decay_half_life_months: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=12.0)
    decay_floor_pct: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.300)
    decay_config_resolution_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = created_at_col()

    org: Mapped["Org"] = relationship(back_populates="dormains")
    circle_dormains: Mapped[list["CircleDormain"]] = relationship(back_populates="dormain")
    competence_scores: Mapped[list["CompetenceScore"]] = relationship(back_populates="dormain")  # type: ignore[name-defined]


class OrgParameter(Base):
    __tablename__ = "org_parameters"
    __table_args__ = (UniqueConstraint("org_id", "parameter"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    parameter: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    resolution_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Circle(Base):
    __tablename__ = "circles"
    __table_args__ = (UniqueConstraint("org_id", "name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    tenets: Mapped[Optional[str]] = mapped_column(Text)
    is_suggested_starter: Mapped[bool] = mapped_column(Boolean, default=False)
    founding_circle: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_col()
    dissolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    dissolution_resolution_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))

    org: Mapped["Org"] = relationship(back_populates="circles")
    dormains: Mapped[list["CircleDormain"]] = relationship(back_populates="circle")
    members: Mapped[list["CircleMember"]] = relationship(back_populates="circle")


class CircleDormain(Base):
    __tablename__ = "circle_dormains"
    __table_args__ = (UniqueConstraint("circle_id", "dormain_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    circle_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("circles.id"), nullable=False)
    dormain_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("dormains.id"), nullable=False)
    mandate_type: Mapped[str] = mapped_column(String(20), nullable=False, default="primary")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    circle: Mapped["Circle"] = relationship(back_populates="dormains")
    dormain: Mapped["Dormain"] = relationship(back_populates="circle_dormains")


class CircleMember(Base):
    __tablename__ = "circle_members"
    __table_args__ = (UniqueConstraint("circle_id", "member_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    circle_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("circles.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"), nullable=False)
    platform_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=True
    )
    display_name_org: Mapped[Optional[str]] = mapped_column(String(300))
    platform_account: Mapped[Optional["PlatformAccount"]] = relationship(back_populates="circle_memberships")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_state: Mapped[MemberState] = mapped_column(String(20), nullable=False, default=MemberState.ACTIVE)
    exited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    exit_record_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("member_exit_records.id"))

    circle: Mapped["Circle"] = relationship(back_populates="members")
    member: Mapped["Member"] = relationship(back_populates="circle_memberships")

class PlatformAccount(Base):
    """Platform-level identity. One per human, across all orgs."""
    __tablename__ = "platform_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    handle:        Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    email:         Mapped[str]           = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str]           = mapped_column(String(255), nullable=False)
    legal_name:    Mapped[Optional[str]] = mapped_column(String(300))
    legal_name_verified:     Mapped[bool]           = mapped_column(Boolean, default=False)
    legal_name_verified_ref: Mapped[Optional[str]]  = mapped_column(String(500))
    legal_name_changed_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at:  Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    wallet_items: Mapped[list["CredentialWallet"]] = relationship(back_populates="account")
    org_memberships: Mapped[list["Member"]] = relationship(back_populates="platform_account")
    circle_memberships: Mapped[list["CircleMember"]] = relationship(back_populates="platform_account")
    invitations: Mapped[list["OrgInvitation"]] = relationship(back_populates="platform_account")


class CredentialWallet(Base):
    """Uploaded credential documents — platform level, not org-verified."""
    __tablename__ = "credential_wallet"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    platform_account_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("platform_accounts.id"), nullable=False
    )
    label:           Mapped[str]           = mapped_column(String(300), nullable=False)
    credential_type: Mapped[str]           = mapped_column(String(50), nullable=False)
    value_claimed:   Mapped[Optional[str]] = mapped_column(String(500))
    vdc_reference:   Mapped[Optional[str]] = mapped_column(String(500))
    file_key:        Mapped[Optional[str]] = mapped_column(String(500))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    account: Mapped["PlatformAccount"] = relationship(back_populates="wallet_items")


class OrgInvitation(Base):
    """Org-initiated invitation to a platform account."""
    __tablename__ = "org_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id:              Mapped[uuid.UUID]           = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False)
    platform_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("platform_accounts.id"))
    invited_by:          Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("members.id"))
    invited_handle:      Mapped[Optional[str]]        = mapped_column(String(100))
    invited_email:       Mapped[Optional[str]]        = mapped_column(String(255))
    message:             Mapped[Optional[str]]        = mapped_column(Text)
    status:     Mapped[str]              = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime]         = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    platform_account: Mapped[Optional["PlatformAccount"]] = relationship(back_populates="invitations")

class MemberApplication(Base):
    """Post-bootstrap membership application — see migration 0003."""
    __tablename__ = "member_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )

    handle:        Mapped[str] = mapped_column(String(100), nullable=False)
    display_name:  Mapped[str] = mapped_column(String(255), nullable=False)
    email:         Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    motivation:              Mapped[Optional[str]] = mapped_column(Text)
    expertise_summary:       Mapped[Optional[str]] = mapped_column(Text)
    proof_of_personhood_ref: Mapped[Optional[str]] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("members.id")
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[Optional[str]]      = mapped_column(Text)

    member_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("members.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
