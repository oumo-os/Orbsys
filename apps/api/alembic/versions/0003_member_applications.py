"""Add member_applications table

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-20 00:00:00

member_applications:
  Post-bootstrap membership application flow.
  Governed by the org's membership_policy parameter:
    'open_application' — anyone can apply, Membership Circle reviews
    'invite_only'      — Membership Circle invites a specific person
    'closed'           — no new members (frozen org)

  On approval: the reviewer triggers Member account creation
  (password_hash stored in the application record, copied to members table).
  On rejection: the application record is kept for audit trail.

  This is the primary post-bootstrap joining path for PAAS orgs.
  The auth/register endpoint is bootstrap-only (founding members only).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),

        # Applicant identity (pre-account creation)
        sa.Column("handle", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),

        # Application content
        sa.Column("motivation", sa.Text),
        sa.Column("expertise_summary", sa.Text),
        sa.Column("proof_of_personhood_ref", sa.String(500)),

        # Status lifecycle: pending → approved | rejected | withdrawn | expired
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="pending"),

        # Reviewer fields (set on approval/rejection)
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_note", sa.Text),

        # Created member_id on approval (FK to members, set after account creation)
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id")),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )

    op.create_index("ix_member_applications_org_status",
                    "member_applications", ["org_id", "status"])
    op.create_index("ix_member_applications_org_handle",
                    "member_applications", ["org_id", "handle"])
    op.create_index("ix_member_applications_created",
                    "member_applications", ["org_id", "created_at"])

    op.execute("GRANT SELECT, INSERT, UPDATE ON member_applications TO orbsys_app")
    op.execute("GRANT SELECT ON member_applications TO orbsys_inferential")


def downgrade() -> None:
    op.drop_table("member_applications")
