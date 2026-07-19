"""
Meridian Collective — Mature Demo Seed
=======================================

Populates the org with realistic data simulating ~6 months of active use:
  - 20 members across all states
  - 20+ commons threads with discussion chains
  - 8 cells (deliberation, motion_review, stf_workspace)
  - 12+ motions in various states
  - 4 STF instances with assignments and verdicts
  - Competence scores, curiosities, delta_c events
  - Notifications, ledger events, org parameters

Run after `seed.py`:
    python -m src.scripts.seed_demo
    python -m src.scripts.seed_demo --org meridian
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


def _ago(days: int, hours: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)


def _future(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _hash(val: str) -> str:
    return hashlib.sha256(val.encode()).hexdigest()[:64]


async def seed_demo(database_url: str, org_slug: str, quiet: bool = False) -> None:
    def log(msg: str) -> None:
        if not quiet:
            print(msg)

    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from src.core.security import hash_password
    from src.models.org import (
        Org, Member, Dormain, Circle, CircleDormain, CircleMember,
        OrgParameter, PlatformAccount, MemberExitRecord,
    )
    from src.models.governance import (
        CommonsThread, CommonsThreadDormainTag, CommonsPost,
        Cell, CellContribution, CellVote, CellInvitedCircle,
        Motion, MotionDirective, MotionSpecification,
        Resolution, STFInstance, STFAssignment, STFVerdict,
        LedgerEvent, Notification,
    )
    from src.models.competence import (
        CompetenceScore, Curiosity, DeltaCEvent, WhCredential,
    )
    from src.models.types import (
        MemberState, CellType, CellState, CellVisibility,
        MotionType, MotionState, STFType, STFState, VerdictType,
        MandateType, DecayFn, ActivityType, ContributionType,
        CredentialType, ResolutionState,
    )

    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        async with db.begin():

            # ── Load existing org ──────────────────────────────────────────
            org = (await db.execute(
                select(Org).where(Org.slug == org_slug)
            )).scalar_one_or_none()
            if not org:
                print(f"Org '{org_slug}' not found — run seed.py first")
                return
            log(f"  Org: {org.name} ({org.id})")

            dormains = (await db.execute(
                select(Dormain).where(Dormain.org_id == org.id)
            )).scalars().all()
            d_map = {d.name: d for d in dormains}
            log(f"  Dormains: {', '.join(d_map.keys())}")

            circles = (await db.execute(
                select(Circle).where(Circle.org_id == org.id)
            )).scalars().all()
            c_map = {c.name: c for c in circles}
            log(f"  Circles: {', '.join(c_map.keys())}")

            # ══════════════════════════════════════════════════════════════
            # 1. MEMBERS (20 total)
            # ══════════════════════════════════════════════════════════════

            MEMBER_SPECS = [
                # handle, display_name, email, state, join_days_ago, expertise (dormain -> level)
                ("founder",       "Meridian Founder",     "founder@meridian.org",   "active",    180, {"Governance": 0.95, "Community": 0.85, "Treasury": 0.70}),
                ("alice_proto",   "Alice Protocolova",    "alice@meridian.org",     "active",    170, {"Protocol Engineering": 0.92, "Security": 0.65}),
                ("bob_governs",   "Bob Governson",        "bob@meridian.org",       "active",    165, {"Governance": 0.88, "Community": 0.55}),
                ("carol_research","Carol Researchwell",   "carol@meridian.org",     "active",    160, {"Research": 0.90, "Protocol Engineering": 0.60}),
                ("dave_sec",      "Dave Securitas",       "dave@meridian.org",      "active",    155, {"Security": 0.93, "Protocol Engineering": 0.70}),
                ("eve_community", "Eve Communis",         "eve@meridian.org",       "active",    150, {"Community": 0.88, "Governance": 0.50}),
                ("frank_treasury","Frank Treasureman",    "frank@meridian.org",     "active",    145, {"Treasury": 0.91, "Governance": 0.45}),
                ("grace_sys",     "Grace Systemova",      "grace@meridian.org",     "active",    130, {"Protocol Engineering": 0.85, "Research": 0.55}),
                ("hank_jud",      "Hank Judicialson",     "hank@meridian.org",      "active",    120, {"Governance": 0.82, "Security": 0.40}),
                ("iris_comms",    "Iris Communica",       "iris@meridian.org",      "active",    110, {"Community": 0.80, "Research": 0.45}),
                ("jack_treas",    "Jack Ledgerman",       "jack@meridian.org",      "active",    100, {"Treasury": 0.78, "Community": 0.35}),
                ("kate_design",   "Kate Prototypova",     "kate@meridian.org",      "probationary", 14, {"Protocol Engineering": 0.45, "Community": 0.30}),
                ("leo_analyst",   "Leo Dataova",          "leo@meridian.org",       "active",    90,  {"Research": 0.75, "Treasury": 0.50}),
                ("mia_dev",       "Mia Buildsworth",      "mia@meridian.org",       "active",    80,  {"Protocol Engineering": 0.80, "Security": 0.45}),
                ("nick_policy",   "Nick Policios",        "nick@meridian.org",      "active",    70,  {"Governance": 0.78, "Community": 0.40}),
                ("olivia_audit",  "Olivia Auditora",      "olivia@meridian.org",    "active",    60,  {"Security": 0.82, "Governance": 0.55}),
                ("peter_research","Peter Innovatson",     "peter@meridian.org",     "active",    50,  {"Research": 0.70, "Protocol Engineering": 0.40}),
                ("quinn_strat",   "Quinn Strategova",     "quinn@meridian.org",     "on_leave",  45,  {"Treasury": 0.65, "Governance": 0.50}),
                ("sam_departed",  "Sam Resignato",        "sam@meridian.org",       "exited",    120, {"Community": 0.40}),
                ("tina_newbie",   "Tina Novakova",        "tina@meridian.org",      "probationary", 5, {"Community": 0.20}),
            ]

            member_map: dict[str, Member] = {}
            pa_map: dict[str, PlatformAccount] = {}

            for handle, display, email, state, join_days, expertise in MEMBER_SPECS:
                existing = (await db.execute(
                    select(Member).where(Member.org_id == org.id, Member.handle == handle)
                )).scalar_one_or_none()
                if existing:
                    member_map[handle] = existing
                    continue

                # Platform account
                pa = (await db.execute(
                    select(PlatformAccount).where(
                        (PlatformAccount.handle == handle) | (PlatformAccount.email == email)
                    )
                )).scalar_one_or_none()
                if not pa:
                    pa = PlatformAccount(
                        handle=handle, email=email,
                        password_hash=hash_password("demo-2025"),
                        created_at=_ago(join_days),
                    )
                    db.add(pa); await db.flush()
                pa_map[handle] = pa

                member = Member(
                    org_id=org.id, handle=handle, display_name=display,
                    email=email, password_hash=hash_password("demo-2025"),
                    platform_account_id=pa.id,
                    joined_at=_ago(join_days), current_state=MemberState(state),
                )
                db.add(member); await db.flush()
                member_map[handle] = member
                log(f"  + Member: @{handle} ({state})")

            # Exit record for sam_departed
            sam = member_map.get("sam_departed")
            if sam:
                exists = (await db.execute(
                    select(MemberExitRecord).where(MemberExitRecord.member_id == sam.id)
                )).scalar_one_or_none()
                if not exists:
                    db.add(MemberExitRecord(
                        member_id=sam.id, org_id=org.id,
                        exit_reason="resignation", exited_at=_ago(60),
                    ))

            # Circle memberships — distribute members across circles
            CIRCLE_MEMBERSHIP = {
                "Governance Circle":       ["founder", "bob_governs", "hank_jud", "nick_policy", "olivia_audit"],
                "System Custodian Circle": ["alice_proto", "dave_sec", "grace_sys", "mia_dev"],
                "Org Integrity Circle":    ["carol_research", "olivia_audit", "dave_sec"],
                "Membership Circle":       ["eve_community", "iris_comms", "bob_governs"],
                "Judicial Circle":         ["hank_jud", "nick_policy", "founder"],
                "Treasury Circle":         ["frank_treasury", "jack_treas", "leo_analyst", "quinn_strat"],
            }

            for cname, handles in CIRCLE_MEMBERSHIP.items():
                circle = c_map.get(cname)
                if not circle:
                    continue
                for h in handles:
                    m = member_map.get(h)
                    if not m:
                        continue
                    exists = (await db.execute(
                        select(CircleMember).where(
                            CircleMember.circle_id == circle.id,
                            CircleMember.member_id == m.id,
                        )
                    )).scalar_one_or_none()
                    if not exists:
                        db.add(CircleMember(
                            circle_id=circle.id, member_id=m.id,
                            platform_account_id=m.platform_account_id,
                            joined_at=m.joined_at, current_state=MemberState.ACTIVE,
                        ))
            await db.flush()

            # ══════════════════════════════════════════════════════════════
            # 2. ORG PARAMETERS
            # ══════════════════════════════════════════════════════════════

            PARAMS = [
                ("membership_policy",      {"value": "open_application"}),
                ("quorum_pct",             {"value": 0.50}),
                ("voting_period_days",     {"value": 7}),
                ("novice_slot_floor_pct",  {"value": 0.25}),
                ("stf_rotation_days",      {"value": 30}),
                ("commons_visibility",     {"value": "members_only"}),
                ("cell_contribution_limit", {"value": 5}),
                ("motion_sponsor_threshold", {"value": 2}),
            ]

            for pname, pvalue in PARAMS:
                exists = (await db.execute(
                    select(OrgParameter).where(
                        OrgParameter.org_id == org.id,
                        OrgParameter.parameter == pname,
                    )
                )).scalar_one_or_none()
                if not exists:
                    db.add(OrgParameter(
                        org_id=org.id, parameter=pname, value=pvalue,
                        applied_at=_ago(170),
                    ))
            await db.flush()

            # ══════════════════════════════════════════════════════════════
            # 3. COMMONS THREADS (20)
            # ══════════════════════════════════════════════════════════════

            THREAD_DATA = [
                # (title, body, author, state, days_ago, dormain_tags, posts)
                (
                    "RFC: Migrate consensus threshold from 50% to 55%",
                    "After reviewing the last 4 cycles of voting data, I noticed that several motions pass with exactly 50% + 1 vote. This slim majority creates ambiguity about org-wide consensus.\n\nProposal: increase the quorum_pct parameter from 0.50 to 0.55. This ensures a genuine majority rather than a coin-flip outcome.\n\nData attached: voting patterns from cycles 1-4.",
                    "bob_governs", "sponsored", 45,
                    ["Governance"], [
                        ("hank_jud", "Agreed. The 50% threshold has caused at least two contested motions this quarter. 55% is more defensible."),
                        ("nick_policy", "I'd like to see the data broken down by dormain. Some domains may have lower participation rates that artificially inflate the close-vote ratio."),
                        ("olivia_audit", "The audit trail confirms the pattern. I support this change."),
                        ("founder", "I'll sponsor this to a cell. The evidence is compelling."),
                    ],
                ),
                (
                    "Competence drift in Security dormain — need vSTF review",
                    "Two members with W_h > 800 in Security have not contributed to any Security-tagged thread in 90+ days. The decay curve alone doesn't explain this — their W_s is still elevated.\n\nI'm flagging this for a vSTF credential audit. The current W_h values may not reflect actual expertise.",
                    "dave_sec", "sponsored", 38,
                    ["Security", "Governance"], [
                        ("olivia_audit", "Confirmed. I've reviewed their recent contributions — none in Security since March. A vSTF is warranted."),
                        ("carol_research", "The decay half-life for Security is 18 months. Given the rapid evolution of security practices, this might need shortening."),
                        ("alice_proto", "Agreed. Protocol Engineering has the same issue but with a 18-month half-life that's already aggressive."),
                    ],
                ),
                (
                    "Community engagement metrics — Q3 review",
                    "Q3 community health metrics are in:\n- Active members: 15/20 (75%)\n- New applications: 3 pending\n- Thread participation rate: 62%\n- Average response time: 18 hours\n\nThe participation rate is below our 70% target. Proposing a community outreach initiative.",
                    "eve_community", "open", 30,
                    ["Community"], [
                        ("iris_comms", "The response time metric is skewed by the on_leave members. Active member response time is 12 hours, which is healthy."),
                        ("bob_governs", "75% active rate is actually good for an org our age. Let's not over-index on one quarter."),
                        ("founder", "I agree with Eve. Let's set a target of 80% for Q4 and track it."),
                    ],
                ),
                (
                    "Treasury report: Q3 budget allocation",
                    "Q3 budget status:\n- Allocated: 12,000 USDC\n- Spent: 8,400 USDC\n- Remaining: 3,600 USDC\n- Burn rate: 2,800/month\n\nAt current rate, we have ~1.3 months of runway. Recommend increasing the allocation or reducing discretionary spending.",
                    "frank_treasury", "sponsored", 25,
                    ["Treasury"], [
                        ("jack_treas", "The bulk of the spend was on infrastructure (40%) and bounties (35%). Both are essential."),
                        ("quinn_strat", "We should consider a treasury motion to increase the monthly allocation by 20%. The org is growing."),
                        ("leo_analyst", "I can run a detailed analysis of spending categories if the Treasury Circle needs it."),
                    ],
                ),
                (
                    "Proposal: Add 'Research' dormain sub-category for AI/ML",
                    "Research is becoming too broad. We have members working on:\n- Consensus algorithms\n- AI/ML governance tools\n- Economic modeling\n\nProposal: create a 'Research > AI/ML' sub-dormain to better track competence in this emerging area.",
                    "carol_research", "open", 22,
                    ["Research", "Governance"], [
                        ("peter_research", "Strongly support. My AI/ML work is currently tagged under Research broadly, which dilutes the signal."),
                        ("grace_sys", "Adding sub-dormains has governance implications. Each new dormain needs decay parameters, circle mandates, etc."),
                        ("bob_governs", "The Governance Circle should review this. It's a structural change, not just a tagging adjustment."),
                    ],
                ),
                (
                    "Motion: Rotate STF assignment pool quarterly",
                    "The same 8 members have been on STF assignments for 3 consecutive cycles. This creates burn risk and limits fresh perspectives.\n\nProposal: mandate quarterly rotation of the STF assignment pool. Members who have served 2+ consecutive cycles get priority de-selection.",
                    "hank_jud", "sponsored", 20,
                    ["Governance"], [
                        ("olivia_audit", "The rotation data supports this. 3 members have filed 4+ verdicts each while 5 members have filed zero."),
                        ("founder", "This aligns with the novice_slot_floor_pct parameter. Let's codify it."),
                    ],
                ),
                (
                    "Security audit: credential wallet integrity",
                    "Routine audit of credential wallet submissions:\n- Total wallets: 18\n- Verified credentials: 14\n- Pending verification: 3\n- Failed verification: 1\n\nThe failed credential was a degree certificate that couldn't be validated against the issuing institution's public registry.",
                    "olivia_audit", "sponsored", 18,
                    ["Security", "Governance"], [
                        ("dave_sec", "The failed credential should trigger a vSTF review. The member's W_h may need adjustment."),
                        ("hank_jud", "Agreed. This falls under the credential_lapse exit reason if the member can't provide alternative proof."),
                    ],
                ),
                (
                    "Protocol Engineering: v2.1 consensus module draft",
                    "Draft specification for the v2.1 consensus module:\n- Reduced block validation time by 40%\n- Added parallel transaction processing\n- Improved fork choice rule\n\nFull spec attached. Looking for reviews from System Custodian Circle members.",
                    "alice_proto", "sponsored", 15,
                    ["Protocol Engineering"], [
                        ("grace_sys", "Reviewed the parallel processing logic. There's a potential race condition in the state transition function. See inline comments."),
                        ("mia_dev", "The benchmark results look promising. 40% improvement is significant."),
                        ("dave_sec", "Security review pending. The new fork choice rule needs formal verification."),
                    ],
                ),
                (
                    "Community: Onboarding pipeline improvements",
                    "Current onboarding metrics:\n- Average time to first contribution: 12 days\n- Drop-off rate: 35%\n- Mentor assignment time: 3 days\n\nProposing: automated mentor assignment, structured first-week tasks, and a buddy system.",
                    "eve_community", "open", 12,
                    ["Community"], [
                        ("iris_comms", "The drop-off rate is concerning. Most new members lose interest in the first week. We need faster time-to-value."),
                        ("bob_governs", "The Membership Circle should own this initiative. I'll add it to our next meeting agenda."),
                    ],
                ),
                (
                    "Treasury: Investment policy framework",
                    "As our treasury grows, we need a formal investment policy. Current holdings are 100% stablecoins.\n\nProposal: allocate up to 20% to low-risk yield strategies (LSTs,蓝筹 DeFi protocols). Remaining 80% stays in stablecoins for operational liquidity.",
                    "frank_treasury", "open", 10,
                    ["Treasury", "Governance"], [
                        ("quinn_strat", "This needs careful risk analysis. The Treasury Circle should model the downside scenarios."),
                        ("leo_analyst", "I can build a risk model. What's our maximum acceptable drawdown?"),
                        ("founder", "Let's table this until we have proper risk modeling. Safety first."),
                    ],
                ),
                (
                    "Judicial Circle: Precedent library update",
                    "The precedent library needs updating with recent case outcomes:\n- Case 2024-03: Coordinated endorsement pattern (inconclusive)\n- Case 2024-04: Credential lapse (member exited)\n- Case 2024-05: Motion deviation (justified)\n\nThese precedents should inform future judicial decisions.",
                    "hank_jud", "sponsored", 8,
                    ["Governance"], [
                        ("nick_policy", "I've drafted the precedent summaries. They need review by the full Judicial Circle before archiving."),
                        ("olivia_audit", "The credential lapse case is particularly important. It sets the standard for W_h verification requirements."),
                    ],
                ),
                (
                    "Research: Evidence quality scoring framework",
                    "The current evidence scoring is subjective. Proposing a structured framework:\n- Source credibility (1-5)\n- Methodology rigor (1-5)\n- Reproducibility (1-5)\n- Sample size adequacy (1-5)\n\nAverage score determines evidence weight in deliberations.",
                    "carol_research", "open", 6,
                    ["Research", "Governance"], [
                        ("peter_research", "This would standardize how we evaluate research contributions. Strong support."),
                        ("bob_governs", "The Governance Circle should review the scoring criteria to ensure they align with our values."),
                    ],
                ),
                (
                    "Membership application: Tina Novakova",
                    "Application from Tina Novakova:\n- Background: Community management, 3 years experience\n- Expertise: Community building, content moderation\n- Motivation: Contribute to decentralized governance\n\nReferences: Eve Communis, Iris Communica",
                    "eve_community", "sponsored", 5,
                    ["Community"], [
                        ("iris_comms", "I can vouch for Tina. She's been active in the community Discord for months."),
                        ("bob_governs", "The Membership Circle should review. Her background is strong but we need to verify her personhood proof."),
                    ],
                ),
                (
                    "Protocol Engineering: Smart contract audit results",
                    "External audit of our governance smart contracts completed. Key findings:\n- 0 critical vulnerabilities\n- 2 medium-severity issues (fixed)\n- 5 low-severity observations (accepted)\n\nFull report available. The contracts are production-ready.",
                    "alice_proto", "sponsored", 4,
                    ["Protocol Engineering", "Security"], [
                        ("dave_sec", "The two medium-severity fixes look correct. I'll add them to the security knowledge base."),
                        ("grace_sys", "The low-severity observations are standard. Nothing blocking deployment."),
                    ],
                ),
                (
                    "Community: Quarterly social event planning",
                    "Q4 social event ideas:\n1. Virtual game night (October)\n2. AMA with founders (November)\n3. Holiday appreciation dinner fund (December)\n\nBudget request: 500 USDC for the quarter.",
                    "iris_comms", "open", 3,
                    ["Community"], [
                        ("eve_community", "Love the AMA idea. Let's get the founders panel confirmed early."),
                        ("frank_treasury", "500 USDC is reasonable for a quarter of events. I'll include it in the next budget proposal."),
                    ],
                ),
                (
                    "Governance: Annual constitutional review",
                    "It's time for our annual constitutional review. Key areas to examine:\n1. Voting thresholds and quorum requirements\n2. STF composition and rotation\n3. Competence scoring parameters\n4. Exit and re-admission policies\n\nThe Governance Circle should lead this review.",
                    "founder", "open", 2,
                    ["Governance"], [
                        ("bob_governs", "I'll draft the review checklist. Each parameter should be evaluated against the last 12 months of data."),
                        ("hank_jud", "The Judicial Circle should contribute precedent analysis for the exit policies."),
                        ("nick_policy", "I'll prepare a summary of all parameter changes since bootstrap."),
                    ],
                ),
            ]

            thread_map: dict[str, CommonsThread] = {}
            for title, body, author, state, days, tags, posts in THREAD_DATA:
                exists = (await db.execute(
                    select(CommonsThread).where(
                        CommonsThread.org_id == org.id,
                        CommonsThread.title == title,
                    )
                )).scalar_one_or_none()
                if exists:
                    thread_map[title] = exists
                    continue

                m = member_map[author]
                sponsored_at = _ago(days - 2) if state == "sponsored" else None
                thread = CommonsThread(
                    org_id=org.id, author_id=m.id,
                    title=title, body=body,
                    state=state,
                    sponsored_at=sponsored_at,
                    created_at=_ago(days),
                )
                db.add(thread); await db.flush()
                thread_map[title] = thread

                # Tags
                for tag_name in tags:
                    dormain = d_map.get(tag_name)
                    if dormain:
                        db.add(CommonsThreadDormainTag(
                            thread_id=thread.id, dormain_id=dormain.id,
                            source="author", tagged_by=m.id,
                            tagged_at=_ago(days),
                        ))

                # Posts
                for i, (post_author, post_body) in enumerate(posts):
                    pa = member_map[post_author]
                    db.add(CommonsPost(
                        thread_id=thread.id, author_id=pa.id,
                        body=post_body,
                        parent_post_id=None,
                        created_at=_ago(days - len(posts) + i),
                    ))
                await db.flush()
                log(f"  + Thread: {title[:55]}… ({len(posts)} posts)")

            # ══════════════════════════════════════════════════════════════
            # 4. CELLS (8)
            # ══════════════════════════════════════════════════════════════

            CELL_DATA = [
                # (type, state, thread_title, initiator, contributions, days)
                (
                    CellType.DELIBERATION, CellState.ARCHIVED,
                    "RFC: Migrate consensus threshold from 50% to 55%",
                    "founder", [
                        ("bob_governs", "The data clearly shows a pattern. I've attached the voting analysis."),
                        ("hank_jud", "Agreed. The 55% threshold is more defensible. I recommend we also add a cooling-off period for close votes."),
                        ("olivia_audit", "The audit data supports this. No objections."),
                        ("founder", "Consensus reached. I'll file the motion to the Governance Circle."),
                    ], 40,
                ),
                (
                    CellType.MOTION_REVIEW, CellState.ACTIVE,
                    "Competence drift in Security dormain — need vSTF review",
                    "dave_sec", [
                        ("olivia_audit", "The two members in question have W_h > 800 but zero Security contributions in 90+ days. This is a clear drift signal."),
                        ("carol_research", "The decay function should handle this, but the 18-month half-life is too generous for Security."),
                        ("alice_proto", "Protocol Engineering has the same issue. We might need a cross-dormain review."),
                        ("dave_sec", "I'm recommending a vSTF credential audit for both members. The findings will determine next steps."),
                    ], 35,
                ),
                (
                    CellType.STF_WORKSPACE, CellState.ACTIVE,
                    "Treasury report: Q3 budget allocation",
                    "frank_treasury", [
                        ("jack_treas", "Infrastructure costs increased 15% this quarter due to node expansion. This is expected growth."),
                        ("leo_analyst", "I've modeled three budget scenarios. The conservative scenario maintains 2-month runway."),
                        ("quinn_strat", "We need to balance growth with sustainability. I propose a 15% allocation increase."),
                        ("frank_treasury", "The Treasury Circle will draft a formal motion for the allocation increase."),
                    ], 22,
                ),
                (
                    CellType.DELIBERATION, CellState.ARCHIVED,
                    "Protocol Engineering: v2.1 consensus module draft",
                    "alice_proto", [
                        ("grace_sys", "Found a potential race condition in the parallel processing module. See inline comments."),
                        ("mia_dev", "The benchmark results are promising. The race condition is fixable without performance regression."),
                        ("dave_sec", "Security review: the new fork choice rule needs formal verification before deployment."),
                        ("alice_proto", "Both issues addressed in v2.1.1. Race condition fixed, formal verification in progress."),
                    ], 12,
                ),
                (
                    CellType.PERIODIC_AUDIT, CellState.ACTIVE,
                    "Security audit: credential wallet integrity",
                    "olivia_audit", [
                        ("dave_sec", "The failed credential was a PhD certificate from a non-accredited institution. The member's W_h needs adjustment."),
                        ("hank_jud", "This is precedent-setting. We need to establish clear criteria for credential validation."),
                        ("olivia_audit", "I'm filing a motion to add a credential_validation_score parameter to the org parameters."),
                    ], 15,
                ),
                (
                    CellType.DELIBERATION, CellState.TEMPORARILY_CLOSED,
                    "Community engagement metrics — Q3 review",
                    "eve_community", [
                        ("iris_comms", "The participation rate is 62%, below our 70% target. But the quality of contributions has improved."),
                        ("bob_governs", "Let's not panic about one quarter. The trend is still positive year-over-year."),
                        ("eve_community", "Agreed, but we should set clear improvement targets for Q4."),
                    ], 28,
                ),
                (
                    CellType.MOTION_REVIEW, CellState.ARCHIVED,
                    "Motion: Rotate STF assignment pool quarterly",
                    "hank_jud", [
                        ("olivia_audit", "The rotation data shows 3 members with 4+ verdicts while 5 members have filed zero. This is unsustainable."),
                        ("founder", "The novice_slot_floor_pct should be adjusted to ensure new members get STF experience."),
                        ("hank_jud", "Consensus: file the motion with a 2-cycle rotation limit."),
                    ], 17,
                ),
                (
                    CellType.CLOSED_CIRCLE, CellState.ACTIVE,
                    "Judicial Circle: Precedent library update",
                    "hank_jud", [
                        ("nick_policy", "I've drafted precedent summaries for cases 2024-03 through 2024-05."),
                        ("olivia_audit", "The credential lapse precedent is particularly important. It sets the standard for W_h verification."),
                        ("hank_jud", "The Judicial Circle approves the precedent library update. Archiving as case law."),
                    ], 5,
                ),
            ]

            cell_map: dict[str, Cell] = {}
            for ctype, cstate, thread_title, initiator, contribs, days in CELL_DATA:
                thread = thread_map.get(thread_title)
                m = member_map[initiator]
                exists = (await db.execute(
                    select(Cell).where(
                        Cell.org_id == org.id,
                        Cell.commons_thread_id == thread.id if thread else text("1=0"),
                    )
                )).scalar_one_or_none()
                if not exists and thread:
                    cell = Cell(
                        org_id=org.id, cell_type=ctype,
                        visibility=CellVisibility.CLOSED,
                        state=cstate,
                        initiating_member_id=m.id,
                        commons_thread_id=thread.id,
                        created_at=_ago(days),
                        state_changed_at=_ago(max(0, days - 5)),
                    )
                    db.add(cell); await db.flush()
                    cell_map[thread_title] = cell

                    # Contributions
                    for ca, cb in contribs:
                        cm = member_map[ca]
                        db.add(CellContribution(
                            cell_id=cell.id, author_id=cm.id,
                            body=cb,
                            contribution_type=ContributionType.DISCUSSION,
                            created_at=_ago(days - 1),
                        ))
                    await db.flush()
                    log(f"  + Cell: {ctype.value} ({cstate.value}) — {len(contribs)} contributions")

            # ══════════════════════════════════════════════════════════════
            # 5. MOTIONS (10)
            # ══════════════════════════════════════════════════════════════

            MOTION_DATA = [
                # (title_excerpt, cell_title, filed_by, motion_type, state, days, spec)
                (
                    "Migrate consensus threshold",
                    "RFC: Migrate consensus threshold from 50% to 55%",
                    "founder", MotionType.SYS_BOUND, MotionState.ENACTED, 38,
                    ("quorum_pct", {"value": 0.55}, "A 55% quorum ensures genuine majority consensus."),
                ),
                (
                    "STF quarterly rotation",
                    "Motion: Rotate STF assignment pool quarterly",
                    "hank_jud", MotionType.SYS_BOUND, MotionState.ACTIVE, 16,
                    ("stf_rotation_days", {"value": 90}, "Quarterly rotation prevents burnout and ensures fresh perspectives."),
                ),
                (
                    "Credential validation framework",
                    "Security audit: credential wallet integrity",
                    "olivia_audit", MotionType.SYS_BOUND, MotionState.VOTED, 14,
                    ("novice_slot_floor_pct", {"value": 0.30}, "Increase novice floor to 30% to ensure new members get STF experience."),
                ),
                (
                    "Treasury allocation increase",
                    "Treasury report: Q3 budget allocation",
                    "frank_treasury", MotionType.NON_SYSTEM, MotionState.ACTIVE, 20,
                    None,
                ),
                (
                    "Community engagement targets",
                    "Community engagement metrics — Q3 review",
                    "eve_community", MotionType.NON_SYSTEM, MotionState.GATE1_PENDING, 25,
                    None,
                ),
                (
                    "Security decay half-life reduction",
                    "Competence drift in Security dormain",
                    "dave_sec", MotionType.SYS_BOUND, MotionState.DRAFT, 33,
                    None,
                ),
                (
                    "Investment policy framework",
                    "Treasury: Investment policy framework",
                    "frank_treasury", MotionType.HYBRID, MotionState.DRAFT, 8,
                    None,
                ),
                (
                    "Annual constitutional review",
                    "Governance: Annual constitutional review",
                    "founder", MotionType.NON_SYSTEM, MotionState.ACTIVE, 1,
                    None,
                ),
                (
                    "Evidence quality scoring",
                    "Research: Evidence quality scoring framework",
                    "carol_research", MotionType.SYS_BOUND, MotionState.REVISION_REQUESTED, 4,
                    ("quorum_pct", {"value": 0.52}, "Intermediate step before full 55% adoption."),
                ),
                (
                    "Membership review process update",
                    "Membership application: Tina Novakova",
                    "bob_governs", MotionType.NON_SYSTEM, MotionState.GATE1_REJECTED, 3,
                    None,
                ),
            ]

            motion_map: dict[str, Motion] = {}
            for title_key, cell_title, filed_by, mtype, state, days, spec in MOTION_DATA:
                cell = cell_map.get(cell_title)
                if not cell:
                    continue
                m = member_map[filed_by]
                exists = (await db.execute(
                    select(Motion).where(
                        Motion.org_id == org.id,
                        Motion.cell_id == cell.id,
                    )
                )).scalar_one_or_none()
                if exists:
                    motion_map[title_key] = exists
                    continue

                motion = Motion(
                    org_id=org.id, cell_id=cell.id,
                    motion_type=mtype, state=state,
                    filed_by=m.id,
                    created_at=_ago(days),
                    crystallised_at=_ago(days - 1) if state not in ("draft",) else None,
                    state_changed_at=_ago(max(0, days - 2)),
                )
                db.add(motion); await db.flush()
                motion_map[title_key] = motion

                # Directive
                db.add(MotionDirective(
                    motion_id=motion.id,
                    body=f"Implement the change to {spec[0] if spec else 'organizational policy'} as described in the motion.",
                    commitments=["Review implementation within 30 days", "Report outcomes to Governance Circle"],
                ))

                # Specification
                if spec:
                    param, new_val, justification = spec
                    db.add(MotionSpecification(
                        motion_id=motion.id, parameter=param,
                        new_value=new_val, justification=justification,
                        pre_validation_status="valid",
                        pre_validated_at=_ago(days - 1),
                    ))

                # Resolution for enacted motions
                if state == MotionState.ENACTED:
                    db.add(Resolution(
                        motion_id=motion.id, org_id=org.id,
                        resolution_ref=f"RES-{org.slug.upper()}-2024-{motion.id.hex[:6].upper()}",
                        state=ResolutionState.ENACTED,
                        implementation_type="sys_parameter",
                        gate2_agent="astf_diff",
                        enacted_at=_ago(days - 3),
                    ))

                await db.flush()
                log(f"  + Motion: {title_key} ({state.value})")

            # ══════════════════════════════════════════════════════════════
            # 6. STF INSTANCES (5)
            # ══════════════════════════════════════════════════════════════

            STF_DATA = [
                # (type, state, mandate, commission_circle, assignments, verdicts, days)
                (
                    STFType.ASTF_PERIODIC, STFState.COMPLETED,
                    "Periodic competence audit for Governance and Community dormains — Q3 cycle",
                    "Org Integrity Circle",
                    [("olivia_audit", "standard"), ("nick_policy", "standard"), ("leo_analyst", "standard")],
                    [("olivia_audit", VerdictType.APPROVE, "Competence scores are within expected ranges. No drift detected."),
                     ("nick_policy", VerdictType.APPROVE, "Governance participation is healthy. Recommend maintaining current parameters."),
                     ("leo_analyst", VerdictType.CONCERNS, "Two members show slight W_s decay but within acceptable bounds.")],
                    60,
                ),
                (
                    STFType.VSTF, STFState.COMPLETED,
                    "Credential audit: Verify W_h claims for Security dormain members with W_h > 600",
                    "System Custodian Circle",
                    [("dave_sec", "standard"), ("alice_proto", "standard"), ("olivia_audit", "standard")],
                    [("dave_sec", VerdictType.FINDING_CONFIRMED, "One member's PhD credential cannot be verified. W_h adjustment recommended."),
                     ("alice_proto", VerdictType.FINDING_CONFIRMED, "Confirmed. The issuing institution is not in the accredited registry."),
                     ("olivia_audit", VerdictType.ADEQUATE, "The audit methodology is sound. Proceed with W_h adjustment.")],
                    30,
                ),
                (
                    STFType.ASTF_MOTION, STFState.ACTIVE,
                    "Review motion: STF quarterly rotation — assess implementation feasibility",
                    "Governance Circle",
                    [("hank_jud", "standard"), ("bob_governs", "standard"), ("founder", "standard")],
                    [],
                    14,
                ),
                (
                    STFType.JSTF, STFState.ACTIVE,
                    "Investigate coordinated endorsement pattern in Research dormain — potential governance manipulation",
                    "Judicial Circle",
                    [("hank_jud", "standard"), ("nick_policy", "standard"), ("olivia_audit", "standard")],
                    [],
                    21,
                ),
                (
                    STFType.ASTF_PERIODIC, STFState.FORMING,
                    "Q4 periodic competence audit — all dormains",
                    "Org Integrity Circle",
                    [],
                    [],
                    30,
                ),
            ]

            stf_map: dict[str, STFInstance] = {}
            for stf_type, stf_state, mandate, circle_name, assignments, verdicts, days in STF_DATA:
                circle = c_map.get(circle_name)
                exists = (await db.execute(
                    select(STFInstance).where(
                        STFInstance.org_id == org.id,
                        STFInstance.mandate == mandate,
                    )
                )).scalar_one_or_none()
                if exists:
                    stf_map[mandate[:40]] = exists
                    continue

                stf = STFInstance(
                    org_id=org.id, stf_type=stf_type,
                    state=stf_state, mandate=mandate,
                    commissioned_by_circle_id=circle.id if circle else None,
                    deadline=_future(7) if stf_state in (STFState.ACTIVE, STFState.FORMING) else None,
                    created_at=_ago(days),
                    completed_at=_ago(days - 5) if stf_state == STFState.COMPLETED else None,
                )
                db.add(stf); await db.flush()
                stf_map[mandate[:40]] = stf

                # Assignments
                for i, (ahandle, slot) in enumerate(assignments):
                    am = member_map[ahandle]
                    assigned = STFAssignment(
                        stf_instance_id=stf.id, member_id=am.id,
                        slot_type=slot,
                        assigned_at=_ago(days),
                        rotation_end=_future(30) if stf_state == STFState.ACTIVE else None,
                        verdict_filed_at=_ago(days - 6) if stf_state == STFState.COMPLETED else None,
                    )
                    db.add(assigned); await db.flush()

                    # Verdicts
                    for vhandle, vtype, rationale in verdicts:
                        if vhandle == ahandle:
                            vm = member_map[vhandle]
                            db.add(STFVerdict(
                                stf_instance_id=stf.id,
                                assignment_id=assigned.id,
                                verdict=vtype,
                                rationale=rationale,
                                filed_at=_ago(days - 6),
                            ))

                await db.flush()
                log(f"  + STF: {stf_type.value} ({stf_state.value}) — {len(assignments)} assignments")

            # ══════════════════════════════════════════════════════════════
            # 7. COMPETENCE SCORES
            # ══════════════════════════════════════════════════════════════

            COMPETENCE_DATA = {
                # handle: {dormain: (w_s, w_h, proof_count)}
                "founder":       {"Governance": (850, 1200, 45), "Community": (600, 900, 30), "Treasury": (450, 700, 18)},
                "alice_proto":   {"Protocol Engineering": (900, 1400, 52), "Security": (400, 600, 15)},
                "bob_governs":   {"Governance": (750, 1100, 38), "Community": (350, 500, 12)},
                "carol_research":{"Research": (820, 1300, 48), "Protocol Engineering": (380, 550, 14)},
                "dave_sec":      {"Security": (880, 1350, 50), "Protocol Engineering": (420, 650, 16)},
                "eve_community": {"Community": (780, 1100, 40), "Governance": (300, 450, 10)},
                "frank_treasury":{"Treasury": (850, 1250, 42), "Governance": (250, 400, 8)},
                "grace_sys":     {"Protocol Engineering": (700, 1000, 32), "Research": (320, 500, 12)},
                "hank_jud":      {"Governance": (680, 950, 28), "Security": (200, 350, 6)},
                "iris_comms":    {"Community": (650, 900, 25), "Research": (250, 400, 8)},
                "jack_treas":    {"Treasury": (620, 850, 22), "Community": (180, 300, 5)},
                "kate_design":   {"Protocol Engineering": (200, 300, 6), "Community": (120, 200, 3)},
                "leo_analyst":   {"Research": (550, 800, 20), "Treasury": (350, 500, 10)},
                "mia_dev":       {"Protocol Engineering": (600, 900, 24), "Security": (220, 350, 7)},
                "nick_policy":   {"Governance": (580, 850, 22), "Community": (200, 350, 6)},
                "olivia_audit":  {"Security": (650, 950, 26), "Governance": (300, 450, 9)},
                "peter_research":{"Research": (480, 700, 16), "Protocol Engineering": (200, 350, 5)},
                "quinn_strat":   {"Treasury": (420, 650, 14), "Governance": (280, 400, 7)},
                "sam_departed":  {"Community": (150, 250, 4)},
                "tina_newbie":   {"Community": (50, 100, 1)},
            }

            for handle, dormain_scores in COMPETENCE_DATA.items():
                m = member_map.get(handle)
                if not m:
                    continue
                for dname, (ws, wh, proofs) in dormain_scores.items():
                    dormain = d_map.get(dname)
                    if not dormain:
                        continue
                    exists = (await db.execute(
                        select(CompetenceScore).where(
                            CompetenceScore.member_id == m.id,
                            CompetenceScore.dormain_id == dormain.id,
                        )
                    )).scalar_one_or_none()
                    if exists:
                        continue

                    db.add(CompetenceScore(
                        member_id=m.id, dormain_id=dormain.id,
                        w_s=ws, w_s_peak=ws + random.randint(10, 100),
                        w_h=wh, volatility_k=60,
                        proof_count=proofs,
                        last_activity_at=_ago(random.randint(1, 30)),
                        mcmp_status="active",
                    ))
            await db.flush()
            log(f"  + Competence scores: {sum(len(v) for v in COMPETENCE_DATA.values())} entries")

            # ══════════════════════════════════════════════════════════════
            # 8. CURIOSITIES
            # ══════════════════════════════════════════════════════════════

            CURIOSITY_DATA = {
                "founder":       {"Treasury": 0.85, "Protocol Engineering": 0.70},
                "alice_proto":   {"Security": 0.80, "Research": 0.65},
                "bob_governs":   {"Community": 0.75, "Research": 0.60},
                "carol_research":{"Protocol Engineering": 0.70, "Governance": 0.55},
                "dave_sec":      {"Protocol Engineering": 0.75, "Governance": 0.50},
                "eve_community": {"Governance": 0.70, "Treasury": 0.45},
                "frank_treasury":{"Governance": 0.65, "Community": 0.50},
                "grace_sys":     {"Research": 0.80, "Security": 0.60},
                "hank_jud":      {"Security": 0.60, "Community": 0.50},
                "iris_comms":    {"Research": 0.65, "Treasury": 0.40},
                "jack_treas":    {"Protocol Engineering": 0.55, "Governance": 0.45},
                "kate_design":   {"Governance": 0.60, "Security": 0.40},
                "leo_analyst":   {"Governance": 0.70, "Protocol Engineering": 0.55},
                "mia_dev":       {"Research": 0.75, "Governance": 0.50},
                "nick_policy":   {"Security": 0.65, "Research": 0.50},
                "olivia_audit":  {"Protocol Engineering": 0.60, "Community": 0.45},
                "peter_research":{"Security": 0.55, "Community": 0.45},
                "quinn_strat":   {"Community": 0.60, "Protocol Engineering": 0.40},
            }

            for handle, signals in CURIOSITY_DATA.items():
                m = member_map.get(handle)
                if not m:
                    continue
                for dname, signal in signals.items():
                    dormain = d_map.get(dname)
                    if not dormain:
                        continue
                    exists = (await db.execute(
                        select(Curiosity).where(
                            Curiosity.member_id == m.id,
                            Curiosity.dormain_id == dormain.id,
                        )
                    )).scalar_one_or_none()
                    if exists:
                        continue
                    db.add(Curiosity(
                        member_id=m.id, dormain_id=dormain.id,
                        signal=signal,
                        declared_at=_ago(random.randint(10, 120)),
                    ))
            await db.flush()
            log(f"  + Curiosities: {sum(len(v) for v in CURIOSITY_DATA.values())} entries")

            # ══════════════════════════════════════════════════════════════
            # 9. NOTIFICATIONS
            # ══════════════════════════════════════════════════════════════

            NOTIF_DATA = [
                ("founder",       "H", "motion_voted",       "Your motion to migrate the quorum threshold has been enacted.", 35),
                ("founder",       "M", "stf_assigned",       "You have been assigned to a new aSTF periodic audit.", 5),
                ("bob_governs",   "M", "motion_sponsored",   "The consensus threshold motion has been sponsored to a cell.", 40),
                ("bob_governs",   "L", "thread_reply",       "Hank Judicialson replied to your thread on community metrics.", 28),
                ("dave_sec",      "H", "credential_alert",   "A vSTF credential audit has found discrepancies in Security W_h claims.", 28),
                ("dave_sec",      "M", "stf_assigned",       "You have been assigned to a vSTF credential audit.", 25),
                ("olivia_audit",  "M", "stf_assigned",       "You have been assigned to a periodic competence audit.", 55),
                ("olivia_audit",  "L", "motion_enacted",     "The credential validation framework motion has been enacted.", 12),
                ("hank_jud",      "H", "stf_commissioned",   "A jSTF has been commissioned to investigate endorsement patterns.", 18),
                ("hank_jud",      "M", "motion_sponsored",   "The STF rotation motion has been sponsored.", 14),
                ("eve_community", "M", "thread_sponsored",   "Your community engagement thread has been sponsored to a cell.", 25),
                ("eve_community", "L", "member_joined",      "Tina Novakova has applied for membership.", 4),
                ("frank_treasury","M", "budget_review",      "Q3 budget allocation needs Treasury Circle review.", 22),
                ("frank_treasury","L", "motion_active",      "A motion to increase treasury allocation is now active.", 18),
                ("carol_research","L", "thread_created",     "A new thread on evidence quality scoring has been created.", 5),
                ("alice_proto",   "M", "audit_complete",     "Smart contract audit completed. 0 critical findings.", 3),
                ("nick_policy",   "L", "precedent_update",   "The Judicial Circle precedent library has been updated.", 3),
                ("grace_sys",     "L", "review_request",     "Your review is requested on the v2.1 consensus module.", 10),
                ("jack_treas",    "L", "budget_report",      "Q3 budget report is ready for review.", 22),
                ("iris_comms",    "L", "event_proposal",     "A social event proposal has been submitted for Q4.", 2),
            ]

            for mhandle, priority, ntype, body, days in NOTIF_DATA:
                m = member_map.get(mhandle)
                if not m:
                    continue
                exists = (await db.execute(
                    select(Notification).where(
                        Notification.member_id == m.id,
                        Notification.body == body,
                    )
                )).scalar_one_or_none()
                if exists:
                    continue
                db.add(Notification(
                    org_id=org.id, member_id=m.id,
                    priority=priority, notification_type=ntype,
                    body=body,
                    read=days > 10,
                    read_at=_ago(days - 5) if days > 10 else None,
                    created_at=_ago(days),
                ))
            await db.flush()
            log(f"  + Notifications: {len(NOTIF_DATA)} entries")

            # ══════════════════════════════════════════════════════════════
            # 10. LEDGER EVENTS
            # ══════════════════════════════════════════════════════════════

            LEDGER_DATA = [
                ("member_registered",   "founder",      "member",   {"handle": "founder", "bootstrap": True}, 180),
                ("member_registered",   "alice_proto",  "member",   {"handle": "alice_proto"}, 170),
                ("member_registered",   "bob_governs",  "member",   {"handle": "bob_governs"}, 165),
                ("member_registered",   "carol_research","member",  {"handle": "carol_research"}, 160),
                ("member_registered",   "dave_sec",     "member",   {"handle": "dave_sec"}, 155),
                ("member_registered",   "eve_community","member",   {"handle": "eve_community"}, 150),
                ("motion_enacted",      "founder",      "motion",   {"title": "Migrate consensus threshold"}, 35),
                ("stf_completed",       "olivia_audit", "stf",      {"type": "astf_periodic", "mandate": "Q3 audit"}, 55),
                ("stf_completed",       "dave_sec",     "stf",      {"type": "vstf", "mandate": "Credential audit"}, 25),
                ("motion_enacted",      "olivia_audit", "motion",   {"title": "Credential validation framework"}, 12),
                ("member_exited",       "sam_departed", "member",   {"reason": "resignation"}, 60),
                ("member_registered",   "kate_design",  "member",   {"handle": "kate_design"}, 14),
                ("member_registered",   "tina_newbie",  "member",   {"handle": "tina_newbie"}, 5),
            ]

            prev_hash = "0" * 64
            for event_type, ehandle, stype, payload, days in LEDGER_DATA:
                m = member_map.get(ehandle)
                exists = (await db.execute(
                    select(LedgerEvent).where(
                        LedgerEvent.org_id == org.id,
                        LedgerEvent.event_type == event_type,
                        LedgerEvent.subject_id == m.id if m else text("1=0"),
                    )
                )).scalar_one_or_none()
                if exists:
                    prev_hash = exists.event_hash
                    continue

                event_id = _uuid()
                raw = f"{org.id}{event_type}{event_id}{json.dumps(payload, sort_keys=True)}"
                event_hash = _hash(raw)
                db.add(LedgerEvent(
                    id=event_id, org_id=org.id,
                    event_type=event_type,
                    subject_id=m.id if m else None,
                    subject_type=stype,
                    payload=payload,
                    triggered_by_member=m.id if m else None,
                    prev_hash=prev_hash,
                    event_hash=event_hash,
                    created_at=_ago(days),
                ))
                prev_hash = event_hash
            await db.flush()
            log(f"  + Ledger events: {len(LEDGER_DATA)} entries")

            # ══════════════════════════════════════════════════════════════
            # 11. WH CREDENTIALS
            # ══════════════════════════════════════════════════════════════

            WH_DATA = [
                ("alice_proto",   "Protocol Engineering", "certification", 800, 120),
                ("alice_proto",   "Security",             "certification", 300, 90),
                ("dave_sec",      "Security",             "degree",        850, 150),
                ("dave_sec",      "Protocol Engineering", "certification", 400, 100),
                ("carol_research","Research",             "degree",        750, 110),
                ("bob_governs",   "Governance",           "certification", 700, 100),
                ("eve_community", "Community",            "certification", 650, 90),
                ("frank_treasury","Treasury",             "degree",        800, 120),
                ("grace_sys",     "Protocol Engineering", "certification", 600, 80),
                ("hank_jud",      "Governance",           "certification", 550, 70),
                ("olivia_audit",  "Security",             "certification", 600, 85),
                ("leo_analyst",   "Research",             "certification", 500, 60),
                ("mia_dev",       "Protocol Engineering", "certification", 550, 75),
                ("nick_policy",   "Governance",           "certification", 500, 65),
            ]

            for whandle, dname, ctype, wh, days in WH_DATA:
                m = member_map.get(whandle)
                dormain = d_map.get(dname)
                if not m or not dormain:
                    continue
                exists = (await db.execute(
                    select(WhCredential).where(
                        WhCredential.member_id == m.id,
                        WhCredential.dormain_id == dormain.id,
                    )
                )).scalar_one_or_none()
                if exists:
                    continue
                db.add(WhCredential(
                    member_id=m.id, dormain_id=dormain.id,
                    credential_type=ctype,
                    value_wh=wh,
                    verified_at=_ago(days),
                    expires_at=_future(365),
                    status="wh_verified",
                ))
            await db.flush()
            log(f"  + WH credentials: {len(WH_DATA)} entries")

            # ── Commit ───────────────────────────────────────────────────
            await db.commit()
            log("")
            log("=" * 60)
            log("  Meridian Collective — Demo seed complete")
            log("=" * 60)
            log(f"  Members:       {len(member_map)}")
            log(f"  Threads:       {len(thread_map)}")
            log(f"  Cells:         {len(cell_map)}")
            log(f"  Motions:       {len(motion_map)}")
            log(f"  STF instances: {len(stf_map)}")
            log(f"  Credentials:   {sum(len(v) for v in COMPETENCE_DATA.values())}")
            log(f"  Curiosities:   {sum(len(v) for v in CURIOSITY_DATA.values())}")
            log(f"  Notifications: {len(NOTIF_DATA)}")
            log(f"  Ledger events: {len(LEDGER_DATA)}")
            log("")
            log("  All accounts use password: demo-2025")
            log("  Login: http://localhost:3000/auth/login")
            log("=" * 60)

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Meridian Collective with demo data")
    parser.add_argument("--db",    default=None)
    parser.add_argument("--org",   default="meridian")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    import os
    db_url = args.db or os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://orbsys_app:change_me@localhost:5432/orbsys",
    )
    asyncio.run(seed_demo(db_url, args.org, args.quiet))


if __name__ == "__main__":
    main()
