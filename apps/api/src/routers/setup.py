"""
First-run / setup routes.

These routes are active only during system bootstrap (no org exists yet,
or the request targets a specific new org in bootstrap state).

POST /setup/templates          List available org templates
POST /setup/create             Create org from template + register first member
GET  /setup/status/{org_id}   Bootstrap progress status
POST /setup/check-proposals    Check if bootstrap_complete Cell should surface
"""
from __future__ import annotations

import uuid as _uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..bootstrap.service import BootstrapService
from ..bootstrap.templates import (
    TEMPLATES,
    all_proposals_for_template,
    extended_templates,
    founding_circle_quorum,
    get_template,
    primary_templates,
)
from ..core.dependencies import DB, PlatformAuth

router = APIRouter(prefix="/setup", tags=["setup"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    template_key: str
    org_size: int                     # from the slider — used for quorum calculation
    handle: str
    display_name: str
    email: str
    password: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/templates")
async def list_templates(extended: bool = False):
    """
    List available org templates for the first-run selector.
    Returns primary (5) by default; set extended=true for all 10.
    """
    return {
        "primary": [
            {
                "key": t.key,
                "label": t.label,
                "tagline": t.tagline,
                "description": t.description,
                "icon": t.icon,
                "parameter_highlights": {
                    k: v for k, v in t.parameters.items()
                    if k in ("pass_threshold_pct", "novice_slot_floor_pct",
                             "membership_policy", "commons_visibility")
                },
                "suggested_circle_count": len(t.suggested_circles),
                "founding_proposal_count": len(all_proposals_for_template(t.key)),
            }
            for t in primary_templates()
        ],
        "extended": [
            {
                "key": t.key,
                "label": t.label,
                "tagline": t.tagline,
                "description": t.description,
                "icon": t.icon,
                "parameter_highlights": {
                    k: v for k, v in t.parameters.items()
                    if k in ("pass_threshold_pct", "novice_slot_floor_pct",
                             "membership_policy", "commons_visibility")
                },
                "suggested_circle_count": len(t.suggested_circles),
                "founding_proposal_count": len(all_proposals_for_template(t.key)),
            }
            for t in extended_templates()
        ],
    }


@router.get("/templates/{key}")
async def get_template_detail(key: str):
    """Full template detail including all founding proposals."""
    tmpl = get_template(key)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{key}' not found")

    proposals = all_proposals_for_template(key)
    return {
        "key": tmpl.key,
        "label": tmpl.label,
        "tagline": tmpl.tagline,
        "description": tmpl.description,
        "icon": tmpl.icon,
        "parameters": tmpl.parameters,
        "suggested_circles": tmpl.suggested_circles,
        "founding_proposals": [
            {
                "key": p.key,
                "title": p.title,
                "mandate": p.mandate,
                "dormain_keys": p.dormain_keys,
                "sequence": p.sequence,
                "mandatory": p.mandatory,
            }
            for p in proposals
        ],
        "founding_circle_quorum_preview": {
            "for_size_10":  {"min": founding_circle_quorum(10)[0],  "target": founding_circle_quorum(10)[1]},
            "for_size_30":  {"min": founding_circle_quorum(30)[0],  "target": founding_circle_quorum(30)[1]},
            "for_size_100": {"min": founding_circle_quorum(100)[0], "target": founding_circle_quorum(100)[1]},
            "for_size_300": {"min": founding_circle_quorum(300)[0], "target": founding_circle_quorum(300)[1]},
        },
    }


@router.post("/create", status_code=201)
async def create_org_from_template(body: CreateOrgRequest, db: DB):
    """
    First-run org creation. No authentication required — this is the entry point.
    Creates the org, seeds Dormains and parameters, registers the first member.
    Returns a session token so the UI can proceed immediately.
    """
    if body.org_size < 3:
        raise HTTPException(
            status_code=422,
            detail="org_size must be at least 3 (minimum founding circle quorum)"
        )

    tmpl = get_template(body.template_key)
    if not tmpl:
        raise HTTPException(status_code=422, detail=f"Unknown template: {body.template_key}")

    result = await BootstrapService(db).create_from_template(
        template_key=body.template_key,
        org_size=body.org_size,
        first_member_handle=body.handle,
        first_member_display_name=body.display_name,
        first_member_email=body.email,
        first_member_password=body.password,
    )

    # Issue PLATFORM tokens, not an org session. The first member lands on
    # their personal dashboard; entering the new org's workspace is a
    # separate POST /auth/enter-org/{org_id} call (same path every member
    # uses to switch into any org). This keeps exactly one issuance pattern
    # for "I am now inside an org" across the whole platform.
    from ..core.security import create_platform_refresh_token, create_platform_token
    access  = create_platform_token(result["platform_account_id"])
    refresh = create_platform_refresh_token(result["platform_account_id"])

    return {
        **result,
        "tokens": {"access_token": access, "refresh_token": refresh},
        "next_steps": {
            "message": (
                f"Organisation created from '{tmpl.label}' template. "
                f"Invite others to register, complete W_h verification, "
                f"and the founding circle will form automatically once "
                f"{result['fc_quorum']['min']}–{result['fc_quorum']['target']} "
                f"members are verified."
            ),
            "founding_circle_quorum": result["fc_quorum"],
        },
    }


@router.get("/status/{org_id}")
async def bootstrap_status(org_id: _uuid.UUID, account: PlatformAuth, db: DB):
    """
    Bootstrap progress for the onboarding UI.
    Returns: verified member count, founding circle status, proposal progress.
    """
    from sqlalchemy import func, select, text

    from ..models.governance import Cell, Motion
    from ..models.org import (
        Circle,
        CircleMember,
        OrgParameter,
    )

    # Verified member count (have at least one enacted W_h credential)
    verified_count = (await db.execute(
        text("""
            SELECT COUNT(DISTINCT wc.member_id) FROM wh_credentials wc
            JOIN members m ON m.id = wc.member_id
            WHERE m.org_id = :oid AND wc.status = 'enacted'
        """),
        {"oid": str(org_id)},
    )).scalar_one() or 0

    # Founding circle status
    fc = (await db.execute(
        select(Circle).where(
            Circle.org_id == org_id,
            Circle.founding_circle.is_(True),
            Circle.dissolved_at.is_(None),
        )
    )).scalar_one_or_none()

    fc_member_count = 0
    if fc:
        fc_member_count = (await db.execute(
            select(func.count(CircleMember.id)).where(
                CircleMember.circle_id == fc.id,
                CircleMember.exited_at.is_(None),
            )
        )).scalar_one()

    # Proposal progress
    tmpl_param = (await db.execute(
        select(OrgParameter).where(
            OrgParameter.org_id == org_id,
            OrgParameter.parameter == "org_template",
        )
    )).scalar_one_or_none()
    template_key = (tmpl_param.value or {}).get("value", "community") if tmpl_param else "community"
    proposals = all_proposals_for_template(template_key)

    proposal_status = []
    for p in proposals:
        cell_row = (await db.execute(
            select(Cell).where(
                Cell.org_id == org_id,
                Cell.metadata_json["bootstrap_proposal_key"].astext == p.key,
            )
        )).scalar_one_or_none()

        cell_state = None
        motion_state = None
        if cell_row:
            cell_state = cell_row.state.value if cell_row.state else None
            motion_row = (await db.execute(
                select(Motion).where(Motion.cell_id == cell_row.id)
                .order_by(Motion.created_at.desc())
            )).scalar_one_or_none()
            motion_state = motion_row.state.value if motion_row else None

        proposal_status.append({
            "key":          p.key,
            "title":        p.title,
            "sequence":     p.sequence,
            "mandatory":    p.mandatory,
            "cell_exists":  cell_row is not None,
            "cell_state":   cell_state,
            "motion_state": motion_state,
            "resolved":     motion_state == "enacted_locked",
        })

    # Quorum params
    min_param = (await db.execute(
        select(OrgParameter).where(
            OrgParameter.org_id == org_id,
            OrgParameter.parameter == "founding_circle_quorum_min",
        )
    )).scalar_one_or_none()
    tgt_param = (await db.execute(
        select(OrgParameter).where(
            OrgParameter.org_id == org_id,
            OrgParameter.parameter == "founding_circle_quorum_target",
        )
    )).scalar_one_or_none()
    fc_min = int((min_param.value or {}).get("value", 3)) if min_param else 3
    fc_tgt = int((tgt_param.value or {}).get("value", 5)) if tgt_param else 5

    mandatory_resolved = all(
        p["resolved"] for p in proposal_status
        if p["mandatory"] and p["key"] != "bootstrap_complete"
    )

    return {
        "org_id": str(org_id),
        "template": template_key,
        "phase": (
            "pre_founding_circle" if not fc else
            "complete" if mandatory_resolved else
            "founding_deliberation"
        ),
        "verified_members": int(verified_count),
        "founding_circle": {
            "formed":       fc is not None,
            "member_count": fc_member_count,
            "quorum_min":   fc_min,
            "quorum_target": fc_tgt,
        },
        "proposals": proposal_status,
        "mandatory_proposals_resolved": mandatory_resolved,
        "bootstrap_complete_surfaced": any(
            p["key"] == "bootstrap_complete" and p["cell_exists"]
            for p in proposal_status
        ),
    }


@router.post("/check-proposals/{org_id}", status_code=200)
async def check_surface_bootstrap_proposal(
    org_id: _uuid.UUID, account: PlatformAuth, db: DB
):
    """
    Check whether mandatory proposals are resolved and surface
    the bootstrap_complete Cell if so.  Idempotent.
    """
    surfaced = await BootstrapService(db).check_surface_bootstrap_proposal(org_id)
    return {"surfaced": surfaced}
