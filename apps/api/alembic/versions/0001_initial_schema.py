"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00

All tables defined from the data model spec.
Append-only triggers applied to audit-critical tables.
Blind role grants applied after table creation.

Append-only tables:
  ledger_events, delta_c_events, delta_c_reviewers,
  cell_contributions, cell_votes, stf_verdicts,
  stf_unsealing_events, commons_posts
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

APPEND_ONLY_TABLES = [
    "ledger_events",
    "delta_c_events",
    "delta_c_reviewers",
    "cell_contributions",
    "cell_votes",
    "stf_verdicts",
    "stf_unsealing_events",
    "commons_posts",
]


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ── Orgs ──────────────────────────────────────────────────────────────────
    op.create_table(
        "orgs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("purpose", sa.Text),
        sa.Column("founding_tenets", sa.Text),
        sa.Column("commons_visibility", sa.String(20), nullable=False,
                  server_default="members_only"),
        sa.Column("bootstrapped_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_orgs_slug", "orgs", ["slug"], unique=True)

    # ── Members ───────────────────────────────────────────────────────────────
    op.create_table(
        "members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("handle", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_state", sa.String(20), nullable=False,
                  server_default="probationary"),
        sa.Column("proof_of_personhood_ref", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "handle", name="uq_members_org_handle"),
    )
    op.create_index("ix_members_org_id", "members", ["org_id"])
    op.create_index("ix_members_org_handle", "members", ["org_id", "handle"])

    op.create_table(
        "member_exit_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("circle_id", postgresql.UUID(as_uuid=True)),  # FK added after circles table
        sa.Column("exit_reason", sa.String(40), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger_ref", postgresql.UUID(as_uuid=True)),
        sa.Column("destination_circle_id", postgresql.UUID(as_uuid=True)),
    )

    # ── Dormains ──────────────────────────────────────────────────────────────
    op.create_table(
        "dormains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id")),
        sa.Column("decay_fn", sa.String(15), nullable=False,
                  server_default="exponential"),
        sa.Column("decay_half_life_months", sa.Numeric(5, 1), nullable=False,
                  server_default="12.0"),
        sa.Column("decay_floor_pct", sa.Numeric(4, 3), nullable=False,
                  server_default="0.300"),
        sa.Column("decay_config_resolution_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "name", name="uq_dormains_org_name"),
    )
    op.create_index("ix_dormains_org_id", "dormains", ["org_id"])

    # ── Org parameters ────────────────────────────────────────────────────────
    op.create_table(
        "org_parameters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("parameter", sa.String(100), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column("resolution_id", postgresql.UUID(as_uuid=True)),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("org_id", "parameter", name="uq_org_parameters_org_param"),
    )

    # ── Circles ───────────────────────────────────────────────────────────────
    op.create_table(
        "circles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("tenets", sa.Text),
        sa.Column("founding_circle", sa.Boolean, nullable=False,
                  server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("dissolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_circles_org_id", "circles", ["org_id"])

    op.create_table(
        "circle_dormains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("circle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("circles.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("mandate_type", sa.String(10), nullable=False,
                  server_default="primary"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("circle_id", "dormain_id", name="uq_circle_dormains_active"),
    )

    op.create_table(
        "circle_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("circle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("circles.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_state", sa.String(20), nullable=False,
                  server_default="probationary"),
        sa.Column("exited_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_circle_members_circle_id", "circle_members", ["circle_id"])
    op.create_index("ix_circle_members_member_id", "circle_members", ["member_id"])

    # Now add deferred FKs for exit records
    op.create_foreign_key(
        "fk_exit_records_circle_id",
        "member_exit_records", "circles",
        ["circle_id"], ["id"],
    )

    # ── Competence ────────────────────────────────────────────────────────────
    op.create_table(
        "competence_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("w_s", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("w_s_peak", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("w_h", sa.Numeric(7, 2), nullable=False, server_default="0"),
        sa.Column("volatility_k", sa.SmallInteger, nullable=False, server_default="60"),
        sa.Column("proof_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("mcmp_status", sa.String(10), nullable=False, server_default="active"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("member_id", "dormain_id", name="uq_competence_scores_member_dormain"),
    )
    op.create_index("ix_competence_scores_member_id", "competence_scores", ["member_id"])
    op.create_index("ix_competence_scores_dormain_ws",
                    "competence_scores", ["dormain_id", "w_s"])

    op.create_table(
        "curiosities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("signal", sa.Numeric(4, 3), nullable=False),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("member_id", "dormain_id", name="uq_curiosities_member_dormain"),
    )

    op.create_table(
        "delta_c_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("gravity_g", sa.Numeric(3, 2), nullable=False),
        sa.Column("volatility_k", sa.SmallInteger, nullable=False),
        sa.Column("delta_raw", sa.Numeric(8, 2), nullable=False),
        sa.Column("delta_applied", sa.Numeric(8, 2), nullable=False),
        sa.Column("ws_before", sa.Numeric(7, 2), nullable=False),
        sa.Column("ws_after", sa.Numeric(7, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="applied"),
        sa.Column("superseded_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("delta_c_events.id")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_delta_c_events_member_dormain",
                    "delta_c_events", ["member_id", "dormain_id"])

    op.create_table(
        "delta_c_reviewers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("delta_c_event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("delta_c_events.id"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("score_s", sa.Numeric(4, 3), nullable=False),
        sa.Column("reviewer_w_d", sa.Numeric(7, 2), nullable=False),
        sa.Column("circle_multiplier_m", sa.Numeric(3, 2), nullable=False),
        sa.Column("provenance_note", sa.Text),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "wh_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("credential_type", sa.String(40), nullable=False),
        sa.Column("value_wh", sa.Numeric(7, 2), nullable=False),
        sa.Column("vdc_reference", sa.String(500)),
        sa.Column("vstf_id", postgresql.UUID(as_uuid=True)),
        sa.Column("resolution_id", postgresql.UUID(as_uuid=True)),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="wh_preliminary"),
    )
    op.create_index("ix_wh_credentials_member_id", "wh_credentials", ["member_id"])

    # ── Commons ───────────────────────────────────────────────────────────────
    op.create_table(
        "commons_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="inherited"),
        sa.Column("state", sa.String(20), nullable=False, server_default="open"),
        sa.Column("freeze_reason", sa.String(20)),
        sa.Column("freeze_ref", postgresql.UUID(as_uuid=True)),
        sa.Column("sponsored_at", sa.DateTime(timezone=True)),
        sa.Column("sponsoring_cell_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_commons_threads_org_id", "commons_threads", ["org_id"])
    op.create_index("ix_commons_threads_org_state",
                    "commons_threads", ["org_id", "state"])

    op.create_table(
        "commons_thread_dormain_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("commons_threads.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("tagged_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id")),
        sa.Column("tagged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("corrected_from_dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id")),
    )
    op.create_index("ix_thread_dormain_tags_thread_id",
                    "commons_thread_dormain_tags", ["thread_id"])

    # commons_posts is append-only
    op.create_table(
        "commons_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("commons_threads.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("parent_post_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("commons_posts.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_commons_posts_thread_id", "commons_posts", ["thread_id"])

    op.create_table(
        "commons_formal_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("post_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("commons_posts.id"), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("score_s", sa.Numeric(4, 3), nullable=False),
        sa.Column("delta_c_event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("delta_c_events.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "post_id", "reviewer_id", "dormain_id",
            name="uq_formal_reviews_post_reviewer_dormain",
        ),
    )

    # ── Cells ─────────────────────────────────────────────────────────────────
    op.create_table(
        "cells",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("cell_type", sa.String(30), nullable=False),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="closed"),
        sa.Column("state", sa.String(25), nullable=False, server_default="active"),
        sa.Column("initiating_member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("parent_cell_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cells.id")),
        sa.Column("commons_thread_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("commons_threads.id")),
        sa.Column("commons_snapshot_at", sa.DateTime(timezone=True)),
        sa.Column("stf_instance_id", postgresql.UUID(as_uuid=True)),
        sa.Column("founding_mandate", sa.Text),
        sa.Column("revision_directive", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cells_org_id", "cells", ["org_id"])

    op.create_table(
        "cell_invited_circles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("cell_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cells.id"), nullable=False),
        sa.Column("circle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("circles.id"), nullable=False),
        sa.Column("invited_because", sa.String(30), nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cell_invited_circles_cell_id",
                    "cell_invited_circles", ["cell_id"])

    # cell_contributions is append-only
    op.create_table(
        "cell_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("cell_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cells.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("contribution_type", sa.String(30), nullable=False,
                  server_default="discussion"),
        sa.Column("commons_post_ref", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("commons_posts.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_cell_contributions_cell_id", "cell_contributions", ["cell_id"])

    op.create_table(
        "cell_composition_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("cell_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cells.id"), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile", postgresql.JSONB, nullable=False),
    )


    # ── Motions ───────────────────────────────────────────────────────────────
    op.create_table(
        "motions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("cell_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cells.id"), nullable=False),
        sa.Column("motion_type", sa.String(15), nullable=False),
        sa.Column("state", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("filed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("insight_draft_ref", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("crystallised_at", sa.DateTime(timezone=True)),
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_motions_org_id", "motions", ["org_id"])
    op.create_index("ix_motions_cell_id", "motions", ["cell_id"])

    # cell_votes is append-only
    op.create_table(
        "cell_votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("cell_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cells.id"), nullable=False),
        sa.Column("motion_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("motions.id"), nullable=False),
        sa.Column("voter_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("dormain_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dormains.id"), nullable=False),
        sa.Column("vote", sa.String(10), nullable=False),
        sa.Column("w_s_at_vote", sa.Numeric(7, 2), nullable=False),
        sa.Column("weight", sa.Numeric(9, 2), nullable=False),
        sa.Column("voted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "motion_id", "voter_id", "dormain_id",
            name="uq_cell_votes_motion_voter_dormain",
        ),
    )
    op.create_index("ix_cell_votes_motion_id", "cell_votes", ["motion_id"])

    # Now we can add FK from cell_votes to motions (motions created after cells)
    # Already defined inline above — motions table exists at this point in the upgrade

    op.create_table(
        "motion_directives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("motion_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("motions.id"), unique=True, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("commitments", postgresql.ARRAY(sa.Text)),
        sa.Column("ambiguities_flagged", postgresql.ARRAY(sa.Text)),
    )

    op.create_table(
        "motion_specifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("motion_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("motions.id"), nullable=False),
        sa.Column("parameter", sa.String(100), nullable=False),
        sa.Column("new_value", postgresql.JSONB, nullable=False),
        sa.Column("justification", sa.Text, nullable=False),
        sa.Column("pre_validation_status", sa.String(30), nullable=False,
                  server_default="pending"),
        sa.Column("pre_validated_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "resolutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("motion_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("motions.id"), unique=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("resolution_ref", sa.String(50), unique=True, nullable=False),
        sa.Column("state", sa.String(30), nullable=False,
                  server_default="pending_implementation"),
        sa.Column("implementation_type", sa.String(30), nullable=False),
        sa.Column("implementing_circle_ids",
                  postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("gate2_agent", sa.String(20), nullable=False),
        sa.Column("enacted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_resolutions_org_id", "resolutions", ["org_id"])

    op.create_table(
        "resolution_gate2_diffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("resolution_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("resolutions.id"), nullable=False),
        sa.Column("parameter", sa.String(100), nullable=False),
        sa.Column("specified_value", postgresql.JSONB, nullable=False),
        sa.Column("applied_value", postgresql.JSONB),
        sa.Column("match", sa.Boolean, nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── STF ───────────────────────────────────────────────────────────────────
    op.create_table(
        "stf_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("stf_type", sa.String(20), nullable=False),
        sa.Column("state", sa.String(15), nullable=False, server_default="forming"),
        sa.Column("mandate", sa.Text, nullable=False),
        sa.Column("commissioned_by_circle_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("circles.id")),
        sa.Column("parent_stf_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("stf_instances.id")),
        sa.Column("motion_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("motions.id")),
        sa.Column("resolution_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("resolutions.id")),
        sa.Column("subject_member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id")),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_stf_instances_org_id", "stf_instances", ["org_id"])
    op.create_index("ix_stf_instances_org_type",
                    "stf_instances", ["org_id", "stf_type"])

    op.create_table(
        "stf_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("stf_instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("stf_instances.id"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id"), nullable=False),
        sa.Column("slot_type", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotation_end", sa.DateTime(timezone=True)),
        sa.Column("isolated_view_token", sa.String(500), unique=True),
        sa.Column("verdict_filed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_stf_assignments_stf_id",
                    "stf_assignments", ["stf_instance_id"])

    # stf_verdicts is append-only
    op.create_table(
        "stf_verdicts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("stf_instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("stf_instances.id"), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("stf_assignments.id"), unique=True, nullable=False),
        sa.Column("verdict", sa.String(30), nullable=False),
        sa.Column("rationale", sa.Text),
        sa.Column("revision_directive", sa.Text),
        sa.Column("checklist", postgresql.JSONB),
        sa.Column("filed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # stf_unsealing_events is append-only
    op.create_table(
        "stf_unsealing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("stf_instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("stf_instances.id"), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("stf_assignments.id"), nullable=False),
        sa.Column("unsealing_condition", sa.String(30), nullable=False),
        sa.Column("triggered_by_ruling_id", postgresql.UUID(as_uuid=True),
                  nullable=False),
        sa.Column("unsealed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── Ledger (append-only, single writer: Integrity Engine) ─────────────────
    op.create_table(
        "ledger_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True)),
        sa.Column("subject_type", sa.String(50)),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("supersedes", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ledger_events.id")),
        sa.Column("triggered_by_member", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("members.id")),
        sa.Column("triggered_by_resolution", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), unique=True, nullable=False),
    )
    op.create_index("ix_ledger_events_org_id", "ledger_events", ["org_id"])
    op.create_index("ix_ledger_events_org_created",
                    "ledger_events", ["org_id", "created_at"])
    op.create_index("ix_ledger_events_event_hash",
                    "ledger_events", ["event_hash"], unique=True)

    # ── Append-only triggers ──────────────────────────────────────────────────
    # enforce_append_only() function was created in init.sql
    # Apply it to all append-only tables
    for table in APPEND_ONLY_TABLES:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION enforce_append_only()
        """)

    # ── Updated_at trigger for members ────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_members_updated_at
        BEFORE UPDATE ON members
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)

    # ── Blind role scoped grants ──────────────────────────────────────────────
    # orbsys_blind can only read stf_assignments (to verify token) and
    # write stf_verdicts. It cannot read any member identity columns.
    op.execute("GRANT SELECT ON stf_assignments TO orbsys_blind")
    op.execute("GRANT INSERT ON stf_verdicts TO orbsys_blind")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO orbsys_blind")

    # Revoke any wider grants that default privileges may have added
    op.execute("REVOKE SELECT ON members FROM orbsys_blind")
    op.execute("REVOKE SELECT ON competence_scores FROM orbsys_blind")
    op.execute("REVOKE SELECT ON delta_c_events FROM orbsys_blind")
    op.execute("REVOKE SELECT ON delta_c_reviewers FROM orbsys_blind")


def downgrade() -> None:
    # Drop triggers first
    for table in APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")

    op.execute("DROP TRIGGER IF EXISTS trg_members_updated_at ON members")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    # Drop tables in reverse dependency order
    for table in [
        "ledger_events",
        "stf_unsealing_events",
        "stf_verdicts",
        "stf_assignments",
        "stf_instances",
        "resolution_gate2_diffs",
        "resolutions",
        "motion_specifications",
        "motion_directives",
        "cell_votes",
        "cell_composition_profiles",
        "cell_contributions",
        "cell_invited_circles",
        "cells",
        "commons_formal_reviews",
        "commons_posts",
        "commons_thread_dormain_tags",
        "commons_threads",
        "wh_credentials",
        "delta_c_reviewers",
        "delta_c_events",
        "curiosities",
        "competence_scores",
        "circle_members",
        "circle_dormains",
        "circles",
        "org_parameters",
        "dormains",
        "member_exit_records",
        "members",
        "motions",
        "orgs",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
