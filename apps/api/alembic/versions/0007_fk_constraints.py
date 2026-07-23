"""Add FK constraints + enums

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-23 00:00:00

Changes:
  cells:                   stf_instance_id  ADD FK → stf_instances.id
  commons_threads:         sponsoring_cell_id  ADD FK → cells.id
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision      = "0007"
down_revision = "0006"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── cells: FK on stf_instance_id ──────────────────────────────────────────
    op.execute("""
        ALTER TABLE cells
        ADD CONSTRAINT fk_cells_stf_instance
        FOREIGN KEY (stf_instance_id) REFERENCES stf_instances(id)
        ON DELETE SET NULL
    """)

    # ── commons_threads: FK on sponsoring_cell_id ─────────────────────────────
    op.execute("""
        ALTER TABLE commons_threads
        ADD CONSTRAINT fk_commons_threads_sponsoring_cell
        FOREIGN KEY (sponsoring_cell_id) REFERENCES cells(id)
        ON DELETE SET NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE cells DROP CONSTRAINT IF EXISTS fk_cells_stf_instance")
    op.execute("ALTER TABLE commons_threads DROP CONSTRAINT IF EXISTS fk_commons_threads_sponsoring_cell")
