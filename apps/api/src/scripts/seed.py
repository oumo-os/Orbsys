import json
"""
Orb Sys Seed Script
===================

Bootstrap: org → dormains → circles → founding member → demo content.

Run after `alembic upgrade head`:
    python -m src.scripts.seed
    python -m src.scripts.seed --org my-org --handle founder --password secret

Idempotent: re-running skips existing records.
Prints everything needed to start using the app.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DEFAULT_ORG_NAME    = "Meridian Collective"
DEFAULT_ORG_SLUG    = "meridian"
DEFAULT_ORG_PURPOSE = (
    "A demonstration organisation for the Orb Sys PAAS governance platform. "
    "Change this in Org settings after bootstrapping."
)
DEFAULT_HANDLE   = "founder"
DEFAULT_DISPLAY  = "Founding Member"
DEFAULT_EMAIL    = "founder@example.com"
DEFAULT_PASSWORD = "change-me-2025"

SEED_DORMAINS = [
    {"name": "Governance",            "description": "Organisational governance, policy, and process design.",
     "decay_half_life_months": 24.0,  "decay_floor_pct": 0.25},
    {"name": "Protocol Engineering",  "description": "Core protocol design, consensus mechanisms, and system parameters.",
     "decay_half_life_months": 18.0,  "decay_floor_pct": 0.20},
    {"name": "Community",             "description": "Member relations, onboarding, and community health.",
     "decay_half_life_months": 30.0,  "decay_floor_pct": 0.30},
    {"name": "Security",              "description": "Security assurance, threat modelling, and audit.",
     "decay_half_life_months": 18.0,  "decay_floor_pct": 0.20},
    {"name": "Treasury",              "description": "Resource allocation, financial oversight, and budget resolutions.",
     "decay_half_life_months": 24.0,  "decay_floor_pct": 0.25},
    {"name": "Research",              "description": "Research methodology, evidence quality, and knowledge generation.",
     "decay_half_life_months": 36.0,  "decay_floor_pct": 0.30},
]

SEED_CIRCLES = [
    {"name": "Governance Circle",        "description": "Constitutional parameters, dormain definitions, voting thresholds.",      "dormain_names": ["Governance"]},
    {"name": "System Custodian Circle",  "description": "System integrity custodianship. Invited on system-related proposals.",   "dormain_names": ["Protocol Engineering"]},
    {"name": "Org Integrity Circle",     "description": "Competence verification, vSTF commissioning, periodic audit scheduling.","dormain_names": ["Governance", "Community"]},
    {"name": "Membership Circle",        "description": "Onboarding pipeline, membership status, judicial track sanctions.",       "dormain_names": ["Community"]},
    {"name": "Judicial Circle",          "description": "jSTF and Meta-aSTF commissioning, due process oversight.",                "dormain_names": ["Governance"]},
    {"name": "Treasury Circle",          "description": "Resource allocation, budget resolutions.",                                "dormain_names": ["Treasury"]},
]

DEMO_THREADS = [
    {
        "title": "Proposal: Reduce novice STF slot floor from 30% to 25%",
        "body": (
            "The current novice_slot_floor_pct of 0.30 was set conservatively at bootstrap. "
            "After three full aSTF cycles, data suggests novice members are contributing "
            "meaningfully at lower allocations. I propose we trial 0.25 and review at the "
            "next periodic audit.\n\n"
            "Evidence: participation data from cycles 1–3 attached. Novice completion rate "
            "is 87%, above the 80% threshold we set as the trigger for a threshold review."
        ),
    },
    {
        "title": "Should the Integrity Engine flag be escalated to jSTF?",
        "body": (
            "The Integrity Engine raised an anomaly flag on a coordinated endorsement pattern "
            "in the Research dormain last week. The Org Integrity Circle reviewed and found "
            "it inconclusive. My question: what's the threshold for escalating to the Judicial "
            "Circle vs. issuing an advisory and closing?\n\n"
            "Looking for input from members with W_s in Governance > 1000."
        ),
    },
    {
        "title": "W_h decay policy — should credentials expire or just decay?",
        "body": (
            "Current setup: W_h is static (doesn't decay). W_s decays if you're inactive. "
            "The academic literature on knowledge half-lives suggests W_h for fast-moving "
            "fields (Security, Protocol Engineering) should have an expiry mechanism — "
            "a credential from 2018 may not reflect current expertise.\n\n"
            "Proposing a sys-bound motion to add an optional expires_at field to W_h claims, "
            "configurable per dormain by the relevant circle."
        ),
    },
]


# ── Agent personas (imported lazily to avoid hard dep) ────────────────────────

AGENT_PERSONAS = [
    {"handle": "alice_proto",    "display_name": "Alice Protocolova", "email": "alice@agents.orbsys.test",   "password": "agent-alice-2025",  "circles": ["System Custodian Circle", "Org Integrity Circle"]},
    {"handle": "bob_governs",    "display_name": "Bob Governson",     "email": "bob@agents.orbsys.test",     "password": "agent-bob-2025",    "circles": ["Governance Circle", "Membership Circle"]},
    {"handle": "carol_research", "display_name": "Carol Researchwell","email": "carol@agents.orbsys.test",   "password": "agent-carol-2025",  "circles": ["Org Integrity Circle"]},
    {"handle": "dave_sec",       "display_name": "Dave Securitas",    "email": "dave@agents.orbsys.test",    "password": "agent-dave-2025",   "circles": ["System Custodian Circle"]},
    {"handle": "eve_community",  "display_name": "Eve Communis",      "email": "eve@agents.orbsys.test",     "password": "agent-eve-2025",    "circles": ["Membership Circle", "Governance Circle"]},
    {"handle": "frank_treasury", "display_name": "Frank Treasureman", "email": "frank@agents.orbsys.test",   "password": "agent-frank-2025",  "circles": ["Treasury Circle"]},
]


async def seed(
    database_url: str,
    org_slug: str,
    org_name: str,
    org_purpose: str,
    handle: str,
    display_name: str,
    email: str,
    password: str,
    quiet: bool = False,
    seed_agents: bool = False,
) -> None:
    def log(msg: str) -> None:
        if not quiet:
            print(msg)

    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from src.core.security import hash_password
    from src.models.org import Org, Dormain, Circle, CircleDormain, CircleMember, Member
    from src.models.governance import CommonsThread, CommonsPost
    from src.models.types import MemberState, DecayFn, MandateType

    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        async with db.begin():

            # ── 1. Org ──────────────────────────────────────────────────────
            org = (await db.execute(select(Org).where(Org.slug == org_slug))).scalar_one_or_none()
            if org:
                log(f"  Org '{org_slug}' exists — skipping")
            else:
                org = Org(name=org_name, slug=org_slug, purpose=org_purpose, bootstrapped_at=None)
                db.add(org)
                await db.flush()
                log(f"✓ Org: {org_name}")

            # ── 2. Dormains ─────────────────────────────────────────────────
            dormain_map: dict[str, Dormain] = {}
            for spec in SEED_DORMAINS:
                d = (await db.execute(
                    select(Dormain).where(Dormain.org_id == org.id, Dormain.name == spec["name"])
                )).scalar_one_or_none()
                if not d:
                    d = Dormain(
                        org_id=org.id, name=spec["name"], description=spec["description"],
                        decay_fn=DecayFn.EXPONENTIAL,
                        decay_half_life_months=spec["decay_half_life_months"],
                        decay_floor_pct=spec["decay_floor_pct"],
                    )
                    db.add(d); await db.flush()
                    log(f"  ✓ Dormain: {spec['name']}")
                dormain_map[spec["name"]] = d

            # ── 3. Circles ──────────────────────────────────────────────────
            circle_map: dict[str, Circle] = {}
            for spec in SEED_CIRCLES:
                c = (await db.execute(
                    select(Circle).where(Circle.org_id == org.id, Circle.name == spec["name"])
                )).scalar_one_or_none()
                if not c:
                    c = Circle(org_id=org.id, name=spec["name"], description=spec["description"], founding_circle=False)
                    db.add(c); await db.flush()
                    for dname in spec["dormain_names"]:
                        if dname in dormain_map:
                            db.add(CircleDormain(
                                circle_id=c.id, dormain_id=dormain_map[dname].id,
                                mandate_type=MandateType.PRIMARY, added_at=datetime.now(timezone.utc),
                            ))
                    await db.flush()
                    log(f"  ✓ Circle: {spec['name']}")
                circle_map[spec["name"]] = c

            # ── 4. Founding member ──────────────────────────────────────────
            member = (await db.execute(
                select(Member).where(Member.org_id == org.id, Member.handle == handle)
            )).scalar_one_or_none()
            if not member:
                member = Member(
                    org_id=org.id, handle=handle, display_name=display_name,
                    email=email, password_hash=hash_password(password),
                    joined_at=datetime.now(timezone.utc), current_state=MemberState.ACTIVE,
                )
                db.add(member); await db.flush()
                log(f"  ✓ Member: @{handle}")
            else:
                log(f"  Member '@{handle}' exists — skipping")

            # Add founder to all circles
            for circle in circle_map.values():
                existing = (await db.execute(
                    select(CircleMember).where(
                        CircleMember.circle_id == circle.id, CircleMember.member_id == member.id
                    )
                )).scalar_one_or_none()
                if not existing:
                    db.add(CircleMember(
                        circle_id=circle.id, member_id=member.id,
                        joined_at=datetime.now(timezone.utc), current_state=MemberState.ACTIVE,
                    ))
            await db.flush()

            # ── 5. Demo Commons threads ─────────────────────────────────────
            for t_spec in DEMO_THREADS:
                exists = (await db.execute(
                    select(CommonsThread).where(
                        CommonsThread.org_id == org.id,
                        CommonsThread.title == t_spec["title"],
                    )
                )).scalar_one_or_none()
                if not exists:
                    thread = CommonsThread(
                        org_id=org.id, author_id=member.id,
                        title=t_spec["title"], body=t_spec["body"],
                        state="open",
                    )
                    db.add(thread); await db.flush()

                    # Add a sample reply
                    db.add(CommonsPost(
                        org_id=org.id, thread_id=thread.id, author_id=member.id,
                        body="Opening this for discussion. Circle members with mandate over "
                             "the relevant dormains are invited to review and sponsor if they "
                             "find the evidence compelling.",
                        parent_post_id=None,
                    ))
                    await db.flush()
                    log(f"  ✓ Thread: {t_spec['title'][:55]}…")

            # ── 6. Agent bots (optional) ────────────────────────────────────
            if seed_agents:
                agents_added = 0
                for agent_spec in AGENT_PERSONAS:
                    existing = (await db.execute(
                        select(Member).where(
                            Member.org_id == org.id,
                            Member.handle == agent_spec["handle"],
                        )
                    )).scalar_one_or_none()

                    if not existing:
                        bot = Member(
                            org_id=org.id,
                            handle=agent_spec["handle"],
                            display_name=agent_spec["display_name"],
                            email=agent_spec["email"],
                            password_hash=hash_password(agent_spec["password"]),
                            joined_at=datetime.now(timezone.utc),
                            current_state=MemberState.ACTIVE,
                        )
                        db.add(bot); await db.flush()

                        for circle_name in agent_spec["circles"]:
                            if circle_name in circle_map:
                                db.add(CircleMember(
                                    circle_id=circle_map[circle_name].id,
                                    member_id=bot.id,
                                    joined_at=datetime.now(timezone.utc),
                                    current_state=MemberState.ACTIVE,
                                ))
                        await db.flush()
                        agents_added += 1
                        log(f"  ✓ Agent bot: @{agent_spec['handle']}")

                if agents_added == 0:
                    log("  Agent bots already exist — skipping")

    await engine.dispose()

    log("")
    log("=" * 60)
    log("  Orb Sys seed complete")
    log("=" * 60)
    log(f"  Org:      {org_name}  (slug: {org_slug})")
    log(f"  Handle:   @{handle}")
    log(f"  Password: {password}")
    log(f"  Email:    {email}")
    log("")
    log("  Login:    http://localhost:3000")
    log("  API docs: http://localhost:8000/docs")
    log("  Blind:    http://localhost:8001/docs")
    log("")
    log("  3 demo Commons threads created. Sponsor one to walk the")
    log("  full Cell → Motion → aSTF → Resolution lifecycle.")
    log("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Orb Sys database")
    parser.add_argument("--db",       default=None)
    parser.add_argument("--org",      default=DEFAULT_ORG_SLUG)
    parser.add_argument("--org-name", default=DEFAULT_ORG_NAME)
    parser.add_argument("--handle",   default=DEFAULT_HANDLE)
    parser.add_argument("--display",  default=DEFAULT_DISPLAY)
    parser.add_argument("--email",    default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--agents", action="store_true",
                        help="Also seed agent bot accounts (requires --agents flag)")
    parser.add_argument("--quiet",  action="store_true")
    args = parser.parse_args()

    import os
    db_url = args.db or os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://orbsys_app:change_me@localhost:5432/orbsys",
    )
    asyncio.run(seed(
        database_url=db_url, org_slug=args.org, org_name=args.org_name,
        org_purpose=DEFAULT_ORG_PURPOSE, handle=args.handle, display_name=args.display,
        email=args.email, password=args.password, quiet=args.quiet,
        seed_agents=args.agents,
    ))


if __name__ == "__main__":
    main()
