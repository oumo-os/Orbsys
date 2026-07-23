"""
STF rubric definitions.

Single source of truth for dimension names, max scores, descriptions,
and flag thresholds. Consumed by:
  - Blind Review API (serving the checklist to reviewers)
  - Integrity Engine (aggregating scores)
  - Blind Review UI (rendering sliders)
  - Ledger (labelling score fields in event payloads)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimension:
    key: str
    label: str
    max_score: int
    description: str
    is_flag: bool = False          # flag dims are separate from health total
    flag_threshold: int | None = None  # score above this raises a risk flag


# ── Motion aSTF rubric (30 pts) ───────────────────────────────────────────────

MOTION_ASTF_DIMENSIONS: list[Dimension] = [
    Dimension(
        key="jurisdiction",
        label="Jurisdiction",
        max_score=9,
        description=(
            "Does the deliberating Circle have clear mandate over this subject? "
            "Score high if the Circle's Dormain mandate directly covers the motion's "
            "domain. Score low if the Circle is acting outside its remit or if "
            "mandate coverage is ambiguous."
        ),
    ),
    Dimension(
        key="depth",
        label="Depth / Effort",
        max_score=5,
        description=(
            "Was the deliberation substantive? Consider: number of contributions, "
            "quality of evidence cited, range of perspectives engaged, length of "
            "deliberation period relative to the decision's stakes."
        ),
    ),
    Dimension(
        key="alignment",
        label="Alignment / Conflict",
        max_score=10,
        description=(
            "Does the motion advance the org's founding tenets and stated purpose? "
            "Are there undisclosed conflicts of interest among deliberation participants? "
            "This is the core legitimacy check — the heaviest dimension."
        ),
    ),
    Dimension(
        key="competence",
        label="Competence",
        max_score=6,
        description=(
            "Were the right people in the deliberation? Consider: W_s distribution "
            "of contributors relative to the motion's domain, whether domain experts "
            "were present and engaged, whether the xSTF composition (if any) was "
            "appropriate to the subject matter."
        ),
    ),
]

MOTION_ASTF_TOTAL = sum(d.max_score for d in MOTION_ASTF_DIMENSIONS)  # 30


# ── p-aSTF Circle rubric (30 pts, all reviewers) ─────────────────────────────
# Based entirely on publicly observable information — Circle profile page,
# Commons activity, motion/resolution record. No access to internal deliberations.

PASTF_CIRCLE_DIMENSIONS: list[Dimension] = [
    Dimension(
        key="activity",
        label="Activity",
        max_score=6,
        description=(
            "Is the Circle visibly active? Consider: Commons threads initiated "
            "or engaged, cells sponsored, motions filed, STF work completed — "
            "all observable from the public record. Score low if the Circle "
            "has been largely absent from governance."
        ),
    ),
    Dimension(
        key="competence_fit",
        label="Competence Fit",
        max_score=7,
        description=(
            "Does the Circle's actual membership W_s match its mandate Dormains? "
            "A Circle mandated over Security should have members with high W_s in "
            "Security-related domains. The system pre-computes a coverage metric "
            "as a data point; your judgment translates that into a score."
        ),
    ),
    Dimension(
        key="discipline",
        label="Discipline",
        max_score=6,
        description=(
            "Does the Circle operate within its mandate? Score high if its motions "
            "and Commons activity clearly stay within its remit. Score low if it "
            "consistently encroaches on other Circles' domains or acts "
            "outside its declared mandate."
        ),
    ),
    Dimension(
        key="cohesion",
        label="Cohesion",
        max_score=5,
        description=(
            "Does the Circle act as a collective or as isolated individuals? "
            "Score high if you observe coordinated positions, joint deliberation, "
            "and shared direction. Score low if members appear to act independently "
            "with no evident alignment to a shared Circle purpose."
        ),
    ),
    Dimension(
        key="delivery",
        label="Delivery",
        max_score=6,
        description=(
            "Does the Circle follow through? Consider: enacted resolutions vs "
            "motions filed, Gate 2 pass rate, revision requests received vs "
            "addressed. A Circle that deliberates but does not deliver, or "
            "that receives repeated Gate 2 failures, scores low here."
        ),
    ),
]

PASTF_CIRCLE_TOTAL = sum(d.max_score for d in PASTF_CIRCLE_DIMENSIONS)  # 30


# ── p-aSTF Member rubric (35 pts health + 2 flag signals) ────────────────────
# Filed only for reviewer's assigned members. Based on member's public
# governance record plus access to their deliberation contributions
# within the Circle.

PASTF_MEMBER_DIMENSIONS: list[Dimension] = [
    Dimension(
        key="effectiveness",
        label="Effectiveness",
        max_score=5,
        description=(
            "Is this member responsive to matters that concern their Circle? "
            "Do they engage with relevant threads and deliberations in a timely way, "
            "or do important matters pass without their input?"
        ),
    ),
    Dimension(
        key="stewardship",
        label="Stewardship",
        max_score=7,
        description=(
            "Does this member's work reflect the org's vision and founding tenets? "
            "Score high if their contributions consistently advance the org's "
            "stated purpose. Score low if they seem to pursue narrower or "
            "competing interests."
        ),
    ),
    Dimension(
        key="participation",
        label="Participation",
        max_score=5,
        description=(
            "Are they present and active? Consider: attendance in deliberations, "
            "vote completion rate, STF assignment fulfilment, Commons engagement. "
            "This is presence, not quality — quality is captured in other dimensions."
        ),
    ),
    Dimension(
        key="investment",
        label="Investment",
        max_score=8,
        description=(
            "Are they genuinely invested in the org's outcomes, or occupying a seat? "
            "Score high if you observe original thinking, initiative, and care. "
            "Score low if their contributions follow the path of least resistance "
            "without adding genuine ownership. The heaviest dimension — "
            "the strongest predictor of governance quality."
        ),
    ),
    Dimension(
        key="productivity",
        label="Productivity",
        max_score=6,
        description=(
            "Do they add something unique and of value? Consider: distinctive "
            "contributions, domain expertise applied, perspectives that wouldn't "
            "exist without them. This is about marginal value, not volume."
        ),
    ),
    Dimension(
        key="role_fit",
        label="Role Fit",
        max_score=4,
        description=(
            "Do they demonstrate understanding of what this Circle's role "
            "requires of them? Score high if their behaviour consistently matches "
            "what the mandate calls for. Score low if they seem uncertain about "
            "their function or frequently act outside their Circle's purpose."
        ),
    ),
]

PASTF_MEMBER_FLAGS: list[Dimension] = [
    Dimension(
        key="replaceability",
        label="Replaceability",
        max_score=5,
        is_flag=True,
        flag_threshold=3,
        description=(
            "Would the organisation lose its way if this member were removed? "
            "Score above 3 if critical knowledge, relationships, or functions are "
            "concentrated in this member with no succession path — a structural risk, "
            "not a quality judgment. Raises a knowledge-transfer mandate."
        ),
    ),
    Dimension(
        key="indispensable",
        label="Indispensable",
        max_score=5,
        is_flag=True,
        flag_threshold=3,
        description=(
            "Would the organisation move closer to its vision if this member "
            "were removed? Score above 3 if this member appears to be actively "
            "blocking progress, capturing governance influence, or obstructing "
            "the org's mandate. Raises a jSTF pre-referral consideration."
        ),
    ),
]

PASTF_MEMBER_HEALTH_TOTAL = sum(
    d.max_score for d in PASTF_MEMBER_DIMENSIONS
)  # 35

# Health tier thresholds (% of combined circle + member health total)
# Applied to each reviewer's score; majority-voted tier is final
HEALTH_TIER_THRESHOLDS = {
    "healthy": 0.75,   # >= 75% → Healthy
    "watch":   0.50,   # >= 50% → Watch
    # < 50% → Concern
}


def motion_astf_total() -> int:
    return MOTION_ASTF_TOTAL


def pastf_total(n_assigned_members: int) -> int:
    """Max possible score for a reviewer with n assigned members."""
    return PASTF_CIRCLE_TOTAL + (PASTF_MEMBER_HEALTH_TOTAL * n_assigned_members)


def health_tier_from_pct(pct: float) -> str:
    if pct >= HEALTH_TIER_THRESHOLDS["healthy"]:
        return "healthy"
    if pct >= HEALTH_TIER_THRESHOLDS["watch"]:
        return "watch"
    return "concern"


def to_dict() -> dict:
    """Serialised rubric definitions for the Blind Review API."""
    return {
        "motion_astf": {
            "dimensions": [
                {"key": d.key, "label": d.label, "max": d.max_score,
                 "description": d.description}
                for d in MOTION_ASTF_DIMENSIONS
            ],
            "total": MOTION_ASTF_TOTAL,
        },
        "periodic_astf": {
            "circle_dimensions": [
                {"key": d.key, "label": d.label, "max": d.max_score,
                 "description": d.description}
                for d in PASTF_CIRCLE_DIMENSIONS
            ],
            "circle_total": PASTF_CIRCLE_TOTAL,
            "member_dimensions": [
                {"key": d.key, "label": d.label, "max": d.max_score,
                 "description": d.description}
                for d in PASTF_MEMBER_DIMENSIONS
            ],
            "member_flags": [
                {"key": d.key, "label": d.label, "max": d.max_score,
                 "description": d.description, "flag_threshold": d.flag_threshold}
                for d in PASTF_MEMBER_FLAGS
            ],
            "member_health_total": PASTF_MEMBER_HEALTH_TOTAL,
            "health_tiers": {
                "healthy": f">= {int(HEALTH_TIER_THRESHOLDS['healthy'] * 100)}%",
                "watch":   f">= {int(HEALTH_TIER_THRESHOLDS['watch'] * 100)}%",
                "concern": f"< {int(HEALTH_TIER_THRESHOLDS['watch'] * 100)}%",
            },
        },
    }
