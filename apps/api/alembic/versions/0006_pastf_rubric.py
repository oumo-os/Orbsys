"""p-aSTF rubric schema

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-23 00:00:00

Changes:
  stf_instances:          + rubric_type      VARCHAR(20)  motion_astf|periodic_astf|vstf|jstf
  stf_assignments:        + assigned_member_ids  JSONB    p-aSTF bipartite assignment
  stf_verdicts:           + dimension_scores JSONB  motion aSTF 4-dim rubric
                          + circle_scores    JSONB  p-aSTF circle-layer rubric
                          + member_scores    JSONB  p-aSTF per-assigned-member rubric
                          + health_tier      VARCHAR(10)  p-aSTF: healthy|watch|concern
                          + risk_flags       JSONB  replaceability/indispensable flags
                          + malpractice_flags JSONB motion aSTF member malpractice refs
  circle_health_snapshots:+ circle_scores    JSONB  aggregated circle rubric
                          + member_breakdowns JSONB aggregated member scores per member_id
                          + risk_flags       JSONB  members with raised flags
                          + health_tier      VARCHAR(10)  majority-voted tier
  members:                + available_for_review  BOOLEAN  standing review availability
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision      = "0006"
down_revision = "0005"
branch_labels = None
depends_on    = None


def upgrade() -> None:

    # ── stf_instances: rubric type ────────────────────────────────────────────
    op.add_column("stf_instances",
        sa.Column("rubric_type", sa.String(20), nullable=True)
        # motion_astf | periodic_astf | vstf | jstf
        # null = pre-migration instances (treated as motion_astf)
    )

    # ── stf_assignments: bipartite assignment for p-aSTF ─────────────────────
    op.add_column("stf_assignments",
        sa.Column("assigned_member_ids", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
        # p-aSTF: list of member UUIDs this reviewer assesses
        # null on motion aSTF, vstf, jstf
    )

    # ── stf_verdicts: rubric payloads ─────────────────────────────────────────
    op.add_column("stf_verdicts",
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
        # motion_astf: {jurisdiction:7, depth:4, alignment:8, competence:5}
    )
    op.add_column("stf_verdicts",
        sa.Column("circle_scores", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
        # periodic_astf circle layer:
        # {activity:5, competence_fit:6, discipline:4, cohesion:4, delivery:5}
    )
    op.add_column("stf_verdicts",
        sa.Column("member_scores", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
        # periodic_astf member layer (only assigned members):
        # [
        #   {
        #     member_id: "uuid",
        #     effectiveness: 4, stewardship: 6, participation: 3,
        #     investment: 7, productivity: 4, role_fit: 3,
        #     replaceability: 2, indispensable: 1,
        #     note: "optional"
        #   }
        # ]
    )
    op.add_column("stf_verdicts",
        sa.Column("health_tier", sa.String(10), nullable=True)
        # periodic_astf: "healthy" | "watch" | "concern"
    )
    op.add_column("stf_verdicts",
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
        # [{member_id, flag_type: "replaceability"|"indispensable", score}]
    )
    op.add_column("stf_verdicts",
        sa.Column("malpractice_flags", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
        # motion_astf: [{member_id, description}]  → triggers jSTF pre-referral
    )

    # ── circle_health_snapshots: create table ──────────────────────────────────
    op.create_table(
        "circle_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("circle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("circles.id"), nullable=False),
        sa.Column("stf_instance_id", postgresql.UUID(as_uuid=True)),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # ── circle_health_snapshots: aggregated results ───────────────────────────
    op.add_column("circle_health_snapshots",
        sa.Column("circle_scores", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
    )
    op.add_column("circle_health_snapshots",
        sa.Column("member_breakdowns", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
        # [{member_id, handle, scores:{...}, health_pts, risk_flags:[...]}]
    )
    op.add_column("circle_health_snapshots",
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True)
    )
    op.add_column("circle_health_snapshots",
        sa.Column("health_tier", sa.String(10), nullable=True)
    )

    # ── members: standing review availability ────────────────────────────────
    op.add_column("members",
        sa.Column("available_for_review", sa.Boolean,
                  nullable=False, server_default="false")
    )
    op.create_index("ix_members_available_for_review",
                    "members", ["org_id", "available_for_review"])

    # Grants
    op.execute("GRANT SELECT, UPDATE ON stf_instances TO orbsys_app")
    op.execute("GRANT SELECT, UPDATE ON stf_assignments TO orbsys_app")


def downgrade() -> None:
    op.drop_column("members", "available_for_review")
    op.drop_column("circle_health_snapshots", "health_tier")
    op.drop_column("circle_health_snapshots", "risk_flags")
    op.drop_column("circle_health_snapshots", "member_breakdowns")
    op.drop_column("circle_health_snapshots", "circle_scores")
    op.drop_column("stf_verdicts", "malpractice_flags")
    op.drop_column("stf_verdicts", "risk_flags")
    op.drop_column("stf_verdicts", "health_tier")
    op.drop_column("stf_verdicts", "member_scores")
    op.drop_column("stf_verdicts", "circle_scores")
    op.drop_column("stf_verdicts", "dimension_scores")
    op.drop_column("stf_assignments", "assigned_member_ids")
    op.drop_column("stf_instances", "rubric_type")
