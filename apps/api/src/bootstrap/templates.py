"""
Org bootstrap templates.

Each template represents a governance archetype. The differentiation is
in parameter defaults and the founding proposal set — not in operations.
Dormains are intentionally broad (academic categories) so they work for
any organisation within the archetype before the founding circle renames them.

Templates are read by:
  - The first-run UI (template selector page)
  - The seed script / bootstrap API
  - The founding proposals seeder

Size tiers adjust founding circle quorum target and a few participation parameters.
They are applied as multipliers on the template base values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Size tiers ─────────────────────────────────────────────────────────────────

SIZE_TIERS = {
    "micro":    {"label": "Micro  (3–15)",    "min": 3,   "max": 15,  "fc_target_pct": 0.40},
    "small":    {"label": "Small  (15–50)",   "min": 15,  "max": 50,  "fc_target_pct": 0.30},
    "medium":   {"label": "Medium (50–200)",  "min": 50,  "max": 200, "fc_target_pct": 0.20},
    "large":    {"label": "Large  (200+)",    "min": 200, "max": 2000,"fc_target_pct": 0.10},
}

FC_MIN = 3     # founding circle never smaller than this
FC_MAX = 13    # founding circle never larger than this


def founding_circle_quorum(size: int) -> tuple[int, int]:
    """Return (min_members, target_members) for the founding circle given org size."""
    for tier in SIZE_TIERS.values():
        if size <= tier["max"]:
            pct = tier["fc_target_pct"]
            break
    else:
        pct = 0.08
    target = max(FC_MIN, min(FC_MAX, round(size * pct)))
    minimum = max(FC_MIN, round(target * 0.6))
    return minimum, target


# ── Dormain templates ─────────────────────────────────────────────────────────
# General academic/professional categories — broadly applicable before the
# founding circle renames them to org-specific terms.

UNIVERSAL_DORMAINS = [
    {
        "name": "Governance",
        "description": "Policy design, decision processes, constitutional questions.",
        "decay_half_life_months": 24,
    },
    {
        "name": "Information Systems",
        "description": "Data, software, infrastructure, and digital tooling.",
        "decay_half_life_months": 12,
    },
    {
        "name": "Human Relations",
        "description": "Member welfare, conflict resolution, culture, and community.",
        "decay_half_life_months": 24,
    },
    {
        "name": "Finance",
        "description": "Resources, budget, fiduciary responsibility, and allocation.",
        "decay_half_life_months": 18,
    },
    {
        "name": "Research & Evidence",
        "description": "Knowledge production, methodology, and evidence standards.",
        "decay_half_life_months": 18,
    },
    {
        "name": "Security & Integrity",
        "description": "Safety, audit, risk, and system integrity.",
        "decay_half_life_months": 12,
    },
    {
        "name": "External Relations",
        "description": "Partnerships, communications, public interface.",
        "decay_half_life_months": 24,
    },
]


# ── Founding proposal definitions ─────────────────────────────────────────────
# Each proposal is an open Cell seeded with a mandate (a question, not a decision).
# The founding circle deliberates and files a motion from each.
# Sequence matters: identity → structure → parameters → bootstrap.

@dataclass
class FoundingProposal:
    key: str              # unique identifier
    title: str
    mandate: str          # the Cell's founding mandate — a question or observation
    dormain_keys: list[str]  # which dormains this is primarily about
    sequence: int         # deliberation order (lower = earlier)
    mandatory: bool = False  # if True, must be resolved before bootstrap proposal surfaces


COMMON_PROPOSALS: list[FoundingProposal] = [
    FoundingProposal(
        key="org_identity",
        title="Organisation identity",
        mandate=(
            "This organisation was bootstrapped from a template and currently carries "
            "a placeholder name and purpose. The founding circle should deliberate on "
            "the permanent name, purpose statement, and founding tenets. "
            "What is this organisation, and what does it exist to do?"
        ),
        dormain_keys=["Governance", "Human Relations"],
        sequence=10,
        mandatory=True,
    ),
    FoundingProposal(
        key="membership_policy",
        title="Who can join and how",
        mandate=(
            "The current membership policy is 'open application', meaning anyone can "
            "apply and the Membership Circle reviews. Should this remain open, or should "
            "joining require an invitation from an existing member? Consider the organisation's "
            "trust model and how it wants to grow."
        ),
        dormain_keys=["Governance", "Human Relations"],
        sequence=20,
    ),
    FoundingProposal(
        key="circle_architecture",
        title="Circle structure",
        mandate=(
            "The template suggests a set of circles with mandate domains. The founding "
            "circle should deliberate on whether this structure fits the organisation's "
            "actual needs. Which circles should exist? What should their mandates be? "
            "Should any be merged, split, or renamed?"
        ),
        dormain_keys=["Governance"],
        sequence=30,
        mandatory=True,
    ),
    FoundingProposal(
        key="voting_thresholds",
        title="Voting thresholds and quorum",
        mandate=(
            "The current voting threshold is set by the template default. Should the "
            "pass threshold be higher for certain kinds of decisions — for example, "
            "constitutional changes or treasury allocations? Should quorum requirements "
            "differ by circle?"
        ),
        dormain_keys=["Governance"],
        sequence=40,
    ),
    FoundingProposal(
        key="competence_policy",
        title="Competence and W_h requirements",
        mandate=(
            "Some circles may require verified external credentials (W_h) for membership. "
            "The founding circle should consider which circles, if any, should have "
            "W_h minimums, and what credential types are relevant for this organisation's "
            "domains."
        ),
        dormain_keys=["Governance", "Research & Evidence"],
        sequence=50,
    ),
    FoundingProposal(
        key="bootstrap_complete",
        title="Complete founding and dissolve the founding circle",
        mandate=(
            "The founding circle has completed its deliberation. This proposal, when "
            "enacted as a Resolution, will complete the bootstrap: the founding circle "
            "will dissolve, all other circles will become active, and the organisation "
            "will enter normal governance operations. "
            "This proposal should only be filed once the identity and circle architecture "
            "proposals have been resolved."
        ),
        dormain_keys=["Governance"],
        sequence=999,
        mandatory=True,
    ),
]


# ── Templates ─────────────────────────────────────────────────────────────────

@dataclass
class OrgTemplate:
    key: str
    label: str
    tagline: str
    description: str
    icon: str            # emoji shown in selector

    # Governance parameter defaults (override base defaults)
    parameters: dict[str, Any] = field(default_factory=dict)

    # Suggested circle definitions (flavour text until founding circle creates them)
    suggested_circles: list[dict] = field(default_factory=list)

    # Template-specific additional proposals (appended to COMMON_PROPOSALS)
    extra_proposals: list[FoundingProposal] = field(default_factory=list)

    # Primary display tier
    primary: bool = True


TEMPLATES: list[OrgTemplate] = [

    # ── PRIMARY FIVE ──────────────────────────────────────────────────────────

    OrgTemplate(
        key="community",
        label="Community Collective",
        tagline="Flat, participatory, inclusion-focused governance",
        description=(
            "For communities, collectives, and purpose-driven groups where broad "
            "participation matters as much as expertise. Optimised for engagement, "
            "low barriers to contribution, and distributed decision-making."
        ),
        icon="⬡",
        parameters={
            "pass_threshold_pct":    0.50,
            "novice_slot_floor_pct": 0.40,
            "membership_policy":     "open_application",
            "commons_visibility":    "public",
            "stf_rotation_weeks_max": 8,
        },
        suggested_circles=[
            {"name": "Governance Circle",    "dormains": ["Governance"]},
            {"name": "Community Circle",     "dormains": ["Human Relations"]},
            {"name": "Membership Circle",    "dormains": ["Human Relations", "Governance"]},
            {"name": "Org Integrity Circle", "dormains": ["Governance"]},
        ],
        extra_proposals=[
            FoundingProposal(
                key="community_commons_policy",
                title="Public access and Commons visibility",
                mandate=(
                    "The Commons is currently set to public — non-members can read and post. "
                    "Should this remain open to the public, or should the Commons be "
                    "members-only? Consider transparency vs. signal quality."
                ),
                dormain_keys=["Governance", "Human Relations"],
                sequence=25,
            ),
        ],
    ),

    OrgTemplate(
        key="dao",
        label="DAO / Crypto Network",
        tagline="Competence-weighted governance replacing token plutocracy",
        description=(
            "For decentralised autonomous organisations and on-chain networks. "
            "Replaces token-weighted voting with contribution-based meritocracy. "
            "Higher thresholds protect against capture; W_h requirements guard "
            "high-stakes treasury and protocol decisions."
        ),
        icon="⛓",
        parameters={
            "pass_threshold_pct":    0.60,
            "novice_slot_floor_pct": 0.25,
            "membership_policy":     "open_application",
            "commons_visibility":    "members_only",
            "stf_rotation_weeks_max": 6,
            "stf_min_size":          4,
        },
        suggested_circles=[
            {"name": "Protocol Circle",      "dormains": ["Information Systems", "Security & Integrity"]},
            {"name": "Treasury Circle",      "dormains": ["Finance"], "wh_min": 1800},
            {"name": "Security Circle",      "dormains": ["Security & Integrity"], "wh_min": 2000},
            {"name": "Community Circle",     "dormains": ["Human Relations"]},
            {"name": "Governance Circle",    "dormains": ["Governance"]},
            {"name": "Org Integrity Circle", "dormains": ["Governance", "Security & Integrity"]},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
            {"name": "Judicial Circle",      "dormains": ["Governance"], "wh_min": 2400},
        ],
        extra_proposals=[
            FoundingProposal(
                key="dao_treasury_gates",
                title="W_h requirements for financial decisions",
                mandate=(
                    "Should the Treasury Circle require verified external credentials "
                    "(finance, legal, or crypto-economics background) for membership? "
                    "Consider the fiduciary responsibility involved in managing on-chain assets."
                ),
                dormain_keys=["Finance", "Governance"],
                sequence=45,
            ),
            FoundingProposal(
                key="dao_protocol_threshold",
                title="Supermajority for protocol changes",
                mandate=(
                    "Protocol and consensus changes are high-stakes and difficult to reverse. "
                    "Should a higher voting threshold (e.g., 0.67 or 0.75) apply to "
                    "protocol-related motions? How would this be implemented?"
                ),
                dormain_keys=["Governance", "Information Systems"],
                sequence=42,
            ),
        ],
    ),

    OrgTemplate(
        key="research",
        label="Research Consortium",
        tagline="Credential-anchored governance for knowledge-intensive collaboration",
        description=(
            "For scientific research groups, academic consortia, and knowledge-intensive "
            "collaborations. Hard competence (W_h) from external credentials is central. "
            "Structured conflict resolution handles authorship and data integrity disputes."
        ),
        icon="⚗",
        parameters={
            "pass_threshold_pct":    0.67,
            "novice_slot_floor_pct": 0.20,
            "membership_policy":     "invite_only",
            "commons_visibility":    "members_only",
            "stf_rotation_weeks_max": 12,
            "stf_min_size":          3,
            "c_max":                 80.0,
        },
        suggested_circles=[
            {"name": "Scientific Council",   "dormains": ["Research & Evidence", "Governance"], "wh_min": 2400},
            {"name": "Data Integrity Circle","dormains": ["Research & Evidence", "Information Systems"], "wh_min": 2000},
            {"name": "Ethics Circle",        "dormains": ["Governance", "Human Relations"], "wh_min": 2200},
            {"name": "Publications Circle",  "dormains": ["Research & Evidence", "External Relations"]},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
            {"name": "Judicial Circle",      "dormains": ["Governance"], "wh_min": 2600},
        ],
        extra_proposals=[
            FoundingProposal(
                key="research_credential_types",
                title="What counts as a verifiable credential here",
                mandate=(
                    "W_h in this system is verified through external credentials. "
                    "For this consortium, what credential types should be recognised? "
                    "Academic degrees, professional licences, publications, grants, patents? "
                    "Define the evidence standards the vSTF will use."
                ),
                dormain_keys=["Research & Evidence", "Governance"],
                sequence=35,
                mandatory=True,
            ),
            FoundingProposal(
                key="research_authorship_policy",
                title="Authorship and attribution standards",
                mandate=(
                    "Research outputs produced under this consortium's governance will need "
                    "clear authorship and attribution standards. Should the org adopt an "
                    "existing framework (CRediT taxonomy, ICMJE) or define its own?"
                ),
                dormain_keys=["Research & Evidence"],
                sequence=55,
            ),
        ],
    ),

    OrgTemplate(
        key="professional",
        label="Professional Association",
        tagline="Standards-setting governance resistant to sub-group capture",
        description=(
            "For professional bodies, industry associations, and standard-setting "
            "organisations. Protects against capture by narrow interests. Transparent "
            "standard-setting defensible to external regulators."
        ),
        icon="⚖",
        parameters={
            "pass_threshold_pct":    0.67,
            "novice_slot_floor_pct": 0.25,
            "membership_policy":     "invite_only",
            "commons_visibility":    "members_only",
            "stf_rotation_weeks_min": 4,
            "stf_rotation_weeks_max": 12,
        },
        suggested_circles=[
            {"name": "Standards Council",    "dormains": ["Governance", "Research & Evidence"], "wh_min": 2200},
            {"name": "Ethics Committee",     "dormains": ["Governance", "Human Relations"], "wh_min": 2200},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
            {"name": "Regulatory Circle",    "dormains": ["Governance", "External Relations"]},
            {"name": "Org Integrity Circle", "dormains": ["Governance"]},
            {"name": "Judicial Circle",      "dormains": ["Governance"], "wh_min": 2600},
        ],
        extra_proposals=[
            FoundingProposal(
                key="professional_licensing",
                title="Credential requirements for membership",
                mandate=(
                    "Professional associations often restrict membership to licensed practitioners. "
                    "Should membership require verified professional credentials? "
                    "Which licences or certifications should qualify?"
                ),
                dormain_keys=["Governance", "Human Relations"],
                sequence=22,
            ),
            FoundingProposal(
                key="professional_standards_scope",
                title="Scope of standards authority",
                mandate=(
                    "What is the scope of this association's standards authority? "
                    "What kinds of decisions require supermajority vs simple majority? "
                    "Define the boundary between operational and constitutional matters."
                ),
                dormain_keys=["Governance"],
                sequence=43,
            ),
        ],
    ),

    OrgTemplate(
        key="opensource",
        label="Open-Source Project",
        tagline="Transparent, contributor-led governance with security gates",
        description=(
            "For open-source software projects and similar contributor communities. "
            "Public Commons enables pre-RFC community engagement. Security-sensitive "
            "decisions are gated by relevant expertise. Maintainer burnout is structurally "
            "mitigated by broad STF participation."
        ),
        icon="◈",
        parameters={
            "pass_threshold_pct":    0.50,
            "novice_slot_floor_pct": 0.40,
            "membership_policy":     "open_application",
            "commons_visibility":    "public",
            "stf_rotation_weeks_min": 1,
            "stf_rotation_weeks_max": 8,
        },
        suggested_circles=[
            {"name": "Core Maintainers",     "dormains": ["Information Systems", "Security & Integrity"], "wh_min": 2000},
            {"name": "Security Circle",      "dormains": ["Security & Integrity"], "wh_min": 2000},
            {"name": "Community Circle",     "dormains": ["Human Relations"]},
            {"name": "Governance Circle",    "dormains": ["Governance"]},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
        ],
        extra_proposals=[
            FoundingProposal(
                key="oss_public_commons",
                title="Public Commons and non-member participation",
                mandate=(
                    "The Commons is public — non-members can read and post. Non-members cannot "
                    "sponsor motions or vote. Is this the right model? Consider pre-RFC feedback "
                    "from downstream users vs. signal quality in governance discussions."
                ),
                dormain_keys=["Governance", "Human Relations"],
                sequence=25,
            ),
            FoundingProposal(
                key="oss_security_disclosure",
                title="Security vulnerability disclosure process",
                mandate=(
                    "Security vulnerabilities require a separate private disclosure path. "
                    "Should the Security Circle operate a private Cell type for embargoed CVEs? "
                    "Define the responsible disclosure timeline and process."
                ),
                dormain_keys=["Security & Integrity", "Governance"],
                sequence=52,
            ),
        ],
    ),

    # ── EXTENDED (behind "view more") ─────────────────────────────────────────

    OrgTemplate(
        key="ngo",
        label="NGO / Non-Profit",
        tagline="Distributed accountability with donor-transparent resource allocation",
        description=(
            "For non-profits, NGOs, and humanitarian organisations. All resource allocation "
            "traces to audited Resolutions. Field office autonomy with central accountability."
        ),
        icon="◎",
        primary=False,
        parameters={
            "pass_threshold_pct":    0.55,
            "novice_slot_floor_pct": 0.35,
            "membership_policy":     "open_application",
            "commons_visibility":    "members_only",
        },
        suggested_circles=[
            {"name": "Programme Circle",     "dormains": ["Governance", "Research & Evidence"]},
            {"name": "Finance Circle",       "dormains": ["Finance"], "wh_min": 1800},
            {"name": "Operations Circle",    "dormains": ["Human Relations", "Information Systems"]},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
            {"name": "Org Integrity Circle", "dormains": ["Governance"]},
        ],
        extra_proposals=[],
    ),

    OrgTemplate(
        key="rnd",
        label="R&D / Innovation Lab",
        tagline="Expert-driven resource allocation replacing bureaucratic approval",
        description=(
            "For internal research teams and innovation labs. Rapid iteration without "
            "sacrificing accountability. Expert-driven allocation; institutional memory "
            "survives team turnover."
        ),
        icon="⬡",
        primary=False,
        parameters={
            "pass_threshold_pct":    0.50,
            "novice_slot_floor_pct": 0.30,
            "membership_policy":     "invite_only",
            "commons_visibility":    "members_only",
            "stf_rotation_weeks_min": 1,
            "stf_rotation_weeks_max": 4,
        },
        suggested_circles=[
            {"name": "Product Circle",       "dormains": ["Governance", "Research & Evidence"]},
            {"name": "Engineering Circle",   "dormains": ["Information Systems"]},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
        ],
        extra_proposals=[],
    ),

    OrgTemplate(
        key="cooperative",
        label="Cooperative / Worker-Owned",
        tagline="Democratic ownership with expertise-weighted operational decisions",
        description=(
            "For worker cooperatives and member-owned enterprises. Democratic legitimacy "
            "for constitutional matters; competence-weighted for operational and "
            "technical decisions."
        ),
        icon="◉",
        primary=False,
        parameters={
            "pass_threshold_pct":    0.50,
            "novice_slot_floor_pct": 0.40,
            "membership_policy":     "invite_only",
            "commons_visibility":    "members_only",
        },
        suggested_circles=[
            {"name": "Governance Circle",    "dormains": ["Governance"]},
            {"name": "Operations Circle",    "dormains": ["Human Relations", "Finance"]},
            {"name": "Finance Circle",       "dormains": ["Finance"], "wh_min": 1600},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
        ],
        extra_proposals=[],
    ),

    OrgTemplate(
        key="holacracy_migration",
        label="Holacracy / Sociocracy Migration",
        tagline="Add independent audit to existing distributed governance",
        description=(
            "For teams migrating from Holacracy, Sociocracy, or similar self-managed "
            "structures. Preserves existing circle architecture while adding the "
            "independent audit layer these systems lack."
        ),
        icon="⊕",
        primary=False,
        parameters={
            "pass_threshold_pct":    0.50,
            "novice_slot_floor_pct": 0.25,
            "membership_policy":     "invite_only",
            "commons_visibility":    "members_only",
        },
        suggested_circles=[
            {"name": "Governance Circle",    "dormains": ["Governance"]},
            {"name": "Org Integrity Circle", "dormains": ["Governance"]},
            {"name": "Judicial Circle",      "dormains": ["Governance"], "wh_min": 2400},
        ],
        extra_proposals=[
            FoundingProposal(
                key="holacracy_role_mapping",
                title="Mapping existing roles to Dormains",
                mandate=(
                    "This org is migrating from an existing self-managed structure. "
                    "Existing roles should be mapped to Dormains, and existing circles "
                    "should be recreated as PAAS Circles with appropriate mandate Dormains. "
                    "The founding circle should deliberate on this mapping."
                ),
                dormain_keys=["Governance"],
                sequence=15,
                mandatory=True,
            ),
        ],
    ),

    OrgTemplate(
        key="platform",
        label="Multi-Stakeholder Platform",
        tagline="Governance across producers, consumers, and intermediaries",
        description=(
            "For platforms with multiple stakeholder classes — producers, consumers, "
            "facilitators, regulators. Each class has legitimate governance interests "
            "that competence-weighting helps balance."
        ),
        icon="◆",
        primary=False,
        parameters={
            "pass_threshold_pct":    0.55,
            "novice_slot_floor_pct": 0.35,
            "membership_policy":     "open_application",
            "commons_visibility":    "public",
        },
        suggested_circles=[
            {"name": "Platform Governance",  "dormains": ["Governance"]},
            {"name": "Community Circle",     "dormains": ["Human Relations"]},
            {"name": "Technical Circle",     "dormains": ["Information Systems"]},
            {"name": "Trust & Safety",       "dormains": ["Security & Integrity", "Governance"]},
            {"name": "Membership Circle",    "dormains": ["Human Relations"]},
        ],
        extra_proposals=[],
    ),
]


# ── Lookup helpers ─────────────────────────────────────────────────────────────

def get_template(key: str) -> OrgTemplate | None:
    return next((t for t in TEMPLATES if t.key == key), None)


def primary_templates() -> list[OrgTemplate]:
    return [t for t in TEMPLATES if t.primary]


def extended_templates() -> list[OrgTemplate]:
    return [t for t in TEMPLATES if not t.primary]


def all_proposals_for_template(template_key: str) -> list[FoundingProposal]:
    """Return COMMON_PROPOSALS + template extra proposals, sorted by sequence."""
    tmpl = get_template(template_key)
    extra = tmpl.extra_proposals if tmpl else []
    combined = COMMON_PROPOSALS + extra
    return sorted(combined, key=lambda p: p.sequence)
