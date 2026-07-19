"""Platform federation layer

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-22 00:00:00

Introduces a platform-level identity layer above org membership.

New tables:
  platform_accounts   — the human (legal_name, handle, email, password)
  credential_wallet   — uploaded credential documents (not verified — org-side only)
  org_invitations     — pending invitations from orgs to platform accounts

Changes to existing tables:
  members             — + platform_account_id FK (nullable, backward compat)
                      — + display_name_org (org-specific alias, nullable)

Identity layers:
  legal_name   platform, hard to change, optional KYC verification link
  handle       platform, globally unique, @identity for invitations/notifications
  display_name org-specific, anything including anonymous personas
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "0005"
down_revision = "0004"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── platform_accounts ────────────────────────────────────────────────────
    op.create_table(
        "platform_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),

        # Identity
        sa.Column("handle", sa.String(100), nullable=False, unique=True),
        sa.Column("email",  sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),

        # Legal name — hard to change, optional verification
        sa.Column("legal_name",              sa.String(300)),
        sa.Column("legal_name_verified",     sa.Boolean,    server_default="false"),
        sa.Column("legal_name_verified_ref", sa.String(500)),   # VDC reference or link
        sa.Column("legal_name_changed_at",   sa.DateTime(timezone=True)),

        # Timestamps
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )

    op.create_index("ix_platform_accounts_handle", "platform_accounts", ["handle"], unique=True)
    op.create_index("ix_platform_accounts_email",  "platform_accounts", ["email"],  unique=True)

    # ── credential_wallet ────────────────────────────────────────────────────
    # Document/link store only — no verification state here.
    # Verification lives in wh_credentials (org-side).
    op.create_table(
        "credential_wallet",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("platform_account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_accounts.id"), nullable=False),

        # What the credential is
        sa.Column("label",           sa.String(300), nullable=False),  # user's own label
        sa.Column("credential_type", sa.String(50),  nullable=False),
        # degree | certification | patent | license | verified_contribution | other
        sa.Column("value_claimed",   sa.String(500)),   # "PhD in CS, MIT, 2018"
        sa.Column("vdc_reference",   sa.String(500)),   # W3C VDC reference or URL
        sa.Column("file_key",        sa.String(500)),   # storage key for uploaded file

        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_index("ix_credential_wallet_account",
                    "credential_wallet", ["platform_account_id"])

    # ── org_invitations ──────────────────────────────────────────────────────
    # An org invites a platform account by handle or email.
    # Distinct from member_applications (applicant initiates) —
    # here the org initiates.
    op.create_table(
        "org_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id",              postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("platform_account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_accounts.id")),
        sa.Column("invited_by",          postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id")),

        # Invitation can be sent to a handle or email before they have an account
        sa.Column("invited_handle", sa.String(100)),
        sa.Column("invited_email",  sa.String(255)),
        sa.Column("message",        sa.Text),

        # status: pending | accepted | declined | expired
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at",    sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at",    sa.DateTime(timezone=True)),
        sa.Column("responded_at",  sa.DateTime(timezone=True)),
    )

    op.create_index("ix_org_invitations_account",
                    "org_invitations", ["platform_account_id"])
    op.create_index("ix_org_invitations_org_status",
                    "org_invitations", ["org_id", "status"])

    # ── members: add platform_account_id ─────────────────────────────────────
    # Nullable — existing rows are backward compat without a platform account.
    op.add_column("members",
        sa.Column("platform_account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_accounts.id"), nullable=True)
    )
    op.create_index("ix_members_platform_account",
                    "members", ["platform_account_id"])

    # Org-specific display alias (nullable — falls back to members.display_name)
    op.add_column("members",
        sa.Column("display_name_org", sa.String(300), nullable=True)
    )

    # Role grants
    op.execute("GRANT SELECT, INSERT, UPDATE ON platform_accounts TO orbsys_app")
    op.execute("GRANT SELECT ON platform_accounts TO orbsys_inferential")
    op.execute("GRANT SELECT ON platform_accounts TO orbsys_insight")
    op.execute("GRANT SELECT, INSERT, UPDATE ON credential_wallet TO orbsys_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON org_invitations TO orbsys_app")

    # ── circle_members: add platform_account_id, display_name_org, exit_record_id ─
    op.add_column("circle_members",
        sa.Column("platform_account_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_accounts.id"), nullable=True)
    )
    op.add_column("circle_members",
        sa.Column("display_name_org", sa.String(300), nullable=True)
    )
    op.add_column("circle_members",
        sa.Column("exit_record_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("member_exit_records.id"), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("circle_members", "exit_record_id")
    op.drop_column("circle_members", "display_name_org")
    op.drop_column("circle_members", "platform_account_id")
    op.drop_index("ix_members_platform_account", "members")
    op.drop_column("members", "display_name_org")
    op.drop_column("members", "platform_account_id")
    op.drop_table("org_invitations")
    op.drop_table("credential_wallet")
    op.drop_table("platform_accounts")
