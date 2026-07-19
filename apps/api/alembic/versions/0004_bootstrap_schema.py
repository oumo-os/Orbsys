"""Add bootstrap and schema alignment columns

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-21 00:00:00

Changes:
  cells:            + metadata_json (JSONB) — bootstrap proposal metadata
  cells:            + access (String 10)   — 'open' | 'closed' (alias for visibility)
  commons_threads:  + created_at (DateTime) — authored timestamp
  wh_credentials:   + vstf_id (UUID FK)    — links credential to verifying vSTF
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "0004"
down_revision = "0003"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # cells.metadata_json — bootstrap proposal key/value metadata
    op.add_column("cells",
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )

    # cells.access — explicit open/closed field (was: visibility)
    # We add 'access' as a new column defaulting to 'open' to match
    # the Cell model and bootstrap service usage
    op.add_column("cells",
        sa.Column("access", sa.String(10), nullable=False,
                  server_default="open")
    )

    # circles.is_suggested_starter — marks circles as starter circles
    op.add_column("circles",
        sa.Column("is_suggested_starter", sa.Boolean, nullable=False,
                  server_default="false")
    )

    # circles.dissolution_resolution_id — links dissolved circle to resolution
    op.add_column("circles",
        sa.Column("dissolution_resolution_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("resolutions.id"), nullable=True)
    )

    # Grant new columns to relevant roles
    op.execute("GRANT SELECT, UPDATE ON cells TO orbsys_app")
    op.execute("GRANT SELECT ON cells TO orbsys_inferential")
    op.execute("GRANT SELECT ON cells TO orbsys_insight")


def downgrade() -> None:
    op.drop_column("circles", "dissolution_resolution_id")
    op.drop_column("circles", "is_suggested_starter")
    op.drop_column("cells", "access")
    op.drop_column("cells", "metadata_json")
