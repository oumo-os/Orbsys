"""Add notifications and feed_scores tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-15 00:00:00

notifications:
  Written by Insight Engine (via Integrity Engine event handler).
  Per-member, per-org, with P1/P2/P3 priority tiers.
  Read status is mutable (not append-only) — members mark as read.
  Insight Engine enforces delivery caps: P2 max 12/day, 3/hour.
  P1 always delivered (bypasses caps).

feed_scores:
  Written by Inferential Engine when relevance is computed.
  Maps (member_id, thread_id) → relevance_score.
  Allows the feed to be ranked by relevance rather than chronological.
  Append-only per (member_id, thread_id) — newer scores supersede via
  application logic (highest created_at wins for a given pair).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("priority", sa.String(3), nullable=False),        # p1 | p2 | p3
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True)),
        sa.Column("subject_type", sa.String(50)),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("action_url", sa.String(500)),                    # deep-link hint
        sa.Column("read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),        # auto-expire stale P3
    )
    op.create_index("ix_notifications_member_org",
                    "notifications", ["member_id", "org_id"])
    op.create_index("ix_notifications_member_unread",
                    "notifications", ["member_id", "read"])
    op.create_index("ix_notifications_created",
                    "notifications", ["member_id", "created_at"])

    # ── feed_scores ───────────────────────────────────────────────────────────
    # Relevance of a Commons thread for a specific member.
    # max(mandate_match, curiosity_match) computed by Inferential Engine.
    op.create_table(
        "feed_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("commons_threads.id"), nullable=False),
        sa.Column("relevance_score", sa.Numeric(5, 4), nullable=False),  # 0.0000–1.0000
        sa.Column("score_basis", sa.String(20), nullable=False,
                  server_default="mandate"),  # mandate | curiosity | combined
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        # Most recent score per (member, thread) is authoritative
        sa.UniqueConstraint("member_id", "thread_id",
                            name="uq_feed_scores_member_thread"),
    )
    op.create_index("ix_feed_scores_member",
                    "feed_scores", ["member_id", "relevance_score"])

    # ── Append-only trigger for feed_scores ───────────────────────────────────
    # feed_scores uses UPSERT (ON CONFLICT DO UPDATE) so no append-only trigger.
    # notifications are mutable (read status) — no trigger either.


def downgrade() -> None:
    op.drop_table("feed_scores")
    op.drop_table("notifications")
