"""
Orb Sys Seed Script
===================

Bootstrap sequence steps 1–4: org → dormains → circles → founding member.

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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_ORG_NAME    = "Meridian Collective"
DEFAULT_ORG_SLUG    = "meridian"
DEFAULT_ORG_PURPOSE = (
    "A demonstration organisation for the Orb Sys PAAS governance platform. "
    "Change this in Org settings after bootstrapping."
)
DEFAULT_HANDLE      = "founder"
DEFAULT_DISPLAY     = "Founding Member"
DEFAULT_EMAIL       = "founder@example.com"
DEFAULT_PASSWORD    = "change-me-2025"

SEED_DORMAINS = [
    {
        "name": "Governance",
        "description": "Organisational governance, policy, and process design.",
        "decay_half_life_months": 24.0,
        "decay_floor_pct": 0.25,
    },
    {
        "name": "Protocol Engineering",
        "description": "Core protocol design, consensus mechanisms, and system parameters.",
        "decay_half_life_months": 18.0,
        "decay_floor_pct": 0.20,
    },
    {
        "name": "Community",
        "description": "Member relations, onboarding, and community health.",
        "decay_half_life_months": 30.0,
        "decay_floor_pct": 0.30,
    },
    {
        "name": "Security",
        "description": "Security assurance, threat modelling, and audit.",
        "decay_half_life_months": 18.0,
        "decay_floor_pct": 0.20,
    },
    {
        "name": "Treasury",
        "description": "Resource allocation, financial oversight, and budget resolutions.",
        "decay_half_life_months": 24.0,
        "decay_floor_pct": 0.25,
    },
    {
        "name": "Research",
        "description": "Research methodology, evidence quality, and knowledge generation.",
        "decay_half_life_months": 36.0,
        "decay_floor_pct": 0.30,
    },
]

SEED_CIRCLES = [
    {
        "name": "Governance Circle",
        "description": "Constitutional parameters, dormain definitions, voting thresholds.",
        "dormain_names": ["Governance"],
    },
    {
        "name": "System Custodian Circle",
        "description": "System integrity custodianship. Invited on system-related proposals.",
        "dormain_names": ["Protocol Engineering"],
    },
    {
        "name": "Org Integrity Circle",
        "description": "Competence verification, vSTF commissioning, periodic audit scheduling.",
        "dormain_names": ["Governance", "Community"],
    },
    {
        "name": "Membership Circle",
        "description": "Onboarding pipeline, membership status, judicial track sanctions.",
        "dormain_names": ["Community"],
    },
    {
        "name": "Judicial Circle",
        "description": "jSTF and Meta-aSTF commissioning, due process oversight.",
        "dormain_names": ["Governance"],
    },
    {
        "name": "Treasury Circle",
        "description": "Resource allocation, budget resolutions.",
        "dormain_names": ["Treasury"],
    },
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
) -> None:
    def log(msg: str) -> None:
        if not quiet:
            print(msg)

    # Import here so script can run without the full app import chain
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    from src.core.security import hash_password
    from src.models.org import Org, Dormain, Circle, CircleDormain, CircleMember, Member
    from src.models.types import MemberState, DecayFn, MandateType

    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionLocal() as db:
        async with db.begin():

            # ── 1. Org ────────────────────────────────────────────────────────
            existing_org = (await db.execute(
                select(Org).where(Org.slug == org_slug)
            )).scalar_one_or_none()

            if existing_org:
                org = existing_org
                log(f"  Org '{org_slug}' already exists — skipping creation")
            else:
                org = Org(
                    name=org_name,
                    slug=org_slug,
                    purpose=org_purpose,
                    bootstrapped_at=None,
                )
                db.add(org)
                await db.flush()
                log(f"✓ Created org: {org_name} (slug: {org_slug})")

            # ── 2. Dormains ───────────────────────────────────────────────────
            dormain_map: dict[str, Dormain] = {}
            for spec in SEED_DORMAINS:
                existing = (await db.execute(
                    select(Dormain).where(
                        Dormain.org_id == org.id,
                        Dormain.name == spec["name"],
                    )
                )).scalar_one_or_none()

                if existing:
                    dormain_map[spec["name"]] = existing
                else:
                    d = Dormain(
                        org_id=org.id,
                        name=spec["name"],
                        description=spec["description"],
                        decay_fn=DecayFn.EXPONENTIAL,
                        decay_half_life_months=spec["decay_half_life_months"],
                        decay_floor_pct=spec["decay_floor_pct"],
                    )
                    db.add(d)
                    await db.flush()
                    dormain_map[spec["name"]] = d
                    log(f"  ✓ Dormain: {spec['name']}")

            # ── 3. Circles ────────────────────────────────────────────────────
            circle_map: dict[str, Circle] = {}
            for spec in SEED_CIRCLES:
                existing = (await db.execute(
                    select(Circle).where(
                        Circle.org_id == org.id,
                        Circle.name == spec["name"],
                    )
                )).scalar_one_or_none()

                if existing:
                    circle_map[spec["name"]] = existing
                else:
                    c = Circle(
                        org_id=org.id,
                        name=spec["name"],
                        description=spec["description"],
                        founding_circle=False,
                    )
                    db.add(c)
                    await db.flush()
                    circle_map[spec["name"]] = c

                    # Assign dormains to circle
                    for dname in spec["dormain_names"]:
                        if dname in dormain_map:
                            cd = CircleDormain(
                                circle_id=c.id,
                                dormain_id=dormain_map[dname].id,
                                mandate_type=MandateType.PRIMARY,
                                added_at=datetime.now(timezone.utc),
                            )
                            db.add(cd)

                    await db.flush()
                    log(f"  ✓ Circle: {spec['name']}")

            # ── 4. Founding member ────────────────────────────────────────────
            existing_member = (await db.execute(
                select(Member).where(
                    Member.org_id == org.id,
                    Member.handle == handle,
                )
            )).scalar_one_or_none()

            if existing_member:
                member = existing_member
                log(f"  Member '{handle}' already exists — skipping creation")
            else:
                member = Member(
                    org_id=org.id,
                    handle=handle,
                    display_name=display_name,
                    email=email,
                    password_hash=hash_password(password),
                    joined_at=datetime.now(timezone.utc),
                    current_state=MemberState.ACTIVE,  # founder starts active
                )
                db.add(member)
                await db.flush()
                log(f"  ✓ Member: @{handle} ({display_name})")

            # Add founder to all circles
            for circle in circle_map.values():
                existing_cm = (await db.execute(
                    select(CircleMember).where(
                        CircleMember.circle_id == circle.id,
                        CircleMember.member_id == member.id,
                    )
                )).scalar_one_or_none()

                if not existing_cm:
                    cm = CircleMember(
                        circle_id=circle.id,
                        member_id=member.id,
                        joined_at=datetime.now(timezone.utc),
                        current_state=MemberState.ACTIVE,
                    )
                    db.add(cm)

            await db.flush()

    await engine.dispose()

    log("")
    log("=" * 60)
    log("  Orb Sys seed complete")
    log("=" * 60)
    log(f"  Org:      {org_name}")
    log(f"  Slug:     {org_slug}")
    log(f"  Handle:   @{handle}")
    log(f"  Password: {password}")
    log(f"  Email:    {email}")
    log("")
    log("  Login at: http://localhost:3000")
    log("  API docs: http://localhost:8000/docs")
    log("")
    log("  Note: org.bootstrapped_at is still null.")
    log("  Complete the founding deliberation via the API to set it,")
    log("  or for dev: POST /org with bootstrapped_at to fast-forward.")
    log("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Orb Sys database")
    parser.add_argument("--db",       default=None, help="Database URL (overrides DATABASE_URL)")
    parser.add_argument("--org",      default=DEFAULT_ORG_SLUG)
    parser.add_argument("--org-name", default=DEFAULT_ORG_NAME)
    parser.add_argument("--handle",   default=DEFAULT_HANDLE)
    parser.add_argument("--display",  default=DEFAULT_DISPLAY)
    parser.add_argument("--email",    default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--quiet",    action="store_true")
    args = parser.parse_args()

    import os
    db_url = args.db or os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://orbsys_app:change_me@localhost:5432/orbsys",
    )

    asyncio.run(seed(
        database_url=db_url,
        org_slug=args.org,
        org_name=args.org_name,
        org_purpose=DEFAULT_ORG_PURPOSE,
        handle=args.handle,
        display_name=args.display,
        email=args.email,
        password=args.password,
        quiet=args.quiet,
    ))


if __name__ == "__main__":
    main()
