"""
Test org provisioning — run once before executing scenarios.

Creates the 'paas-sim' org with dormains and circles via the public API.
The org stays in bootstrap state (bootstrapped_at=null) so self-registration
remains open indefinitely — agents self-register as they're spawned.

Usage:
    python setup.py
    python setup.py --api http://staging.example.com:8000
    python setup.py --reset   # delete and recreate (for clean runs)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import httpx

from config import API_URL, TEST_ORG_SLUG, TEST_ORG_NAME, TEST_ORG_DORMAINS, TEST_ORG_CIRCLES

FOUNDER_HANDLE   = "sim-founder"
FOUNDER_PASSWORD = "sim-founder-2025"
FOUNDER_EMAIL    = "founder@sim.orbsys.test"


async def setup(api_url: str, force: bool = False) -> None:
    async with httpx.AsyncClient(timeout=30) as client:

        # ── 1. Wait for API ──────────────────────────────────────────────────
        print(f"Connecting to API at {api_url}…")
        for attempt in range(20):
            try:
                r = await client.get(f"{api_url}/health")
                if r.status_code == 200:
                    print("API healthy ✓")
                    break
            except Exception:
                pass
            await asyncio.sleep(3)
            print(f"  waiting… ({attempt+1}/20)")
        else:
            print("ERROR: API not reachable")
            sys.exit(1)

        # ── 2. Create org (idempotent) ───────────────────────────────────────
        print(f"\nProvisioning org '{TEST_ORG_SLUG}'…")
        r = await client.post(f"{api_url}/org", json={
            "name": TEST_ORG_NAME,
            "slug": TEST_ORG_SLUG,
            "purpose": (
                "Simulation environment for testing the PAAS governance framework. "
                "This org remains in bootstrap state to permit dynamic agent registration."
            ),
        })
        if r.status_code == 201:
            org = r.json()
            print(f"  ✓ Org created: {org['id']}")
        elif r.status_code == 409:
            print(f"  Org already exists — continuing")
        else:
            print(f"  ERROR: {r.status_code} {r.text[:200]}")
            sys.exit(1)

        # ── 3. Register founder (needed to create dormains and circles) ──────
        print(f"\nRegistering founder @{FOUNDER_HANDLE}…")
        r = await client.post(
            f"{api_url}/auth/register",
            params={"org_slug": TEST_ORG_SLUG},
            json={
                "handle": FOUNDER_HANDLE,
                "display_name": "Simulation Founder",
                "email": FOUNDER_EMAIL,
                "password": FOUNDER_PASSWORD,
            },
        )
        if r.status_code in (200, 201):
            print(f"  ✓ Founder registered")
        elif r.status_code == 409:
            print(f"  Founder already exists — continuing")
        else:
            print(f"  Founder registration: {r.status_code} — continuing anyway")

        # Login as founder
        r = await client.post(f"{api_url}/auth/login", json={
            "org_slug": TEST_ORG_SLUG,
            "handle": FOUNDER_HANDLE,
            "password": FOUNDER_PASSWORD,
        })
        if r.status_code != 200:
            print(f"ERROR: founder login failed {r.status_code}")
            sys.exit(1)
        token = r.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  ✓ Logged in")

        # ── 4. Dormains ──────────────────────────────────────────────────────
        print(f"\nCreating dormains…")
        dormain_map: dict[str, str] = {}

        # Check existing
        r = await client.get(f"{api_url}/competence/dormains", headers=headers)
        existing_dormains = {d["name"]: d["id"] for d in (r.json() if r.status_code == 200 else [])}
        dormain_map.update(existing_dormains)

        for spec in TEST_ORG_DORMAINS:
            if spec["name"] in existing_dormains:
                print(f"  Dormain '{spec['name']}' exists")
                continue
            r = await client.post(f"{api_url}/org/dormains", headers=headers, json={
                "name": spec["name"],
                "description": spec["description"],
            })
            if r.status_code == 201:
                dormain_map[spec["name"]] = r.json()["id"]
                print(f"  ✓ Dormain: {spec['name']}")
            else:
                print(f"  WARNING dormain '{spec['name']}': {r.status_code} {r.text[:80]}")

        # ── 5. Circles ───────────────────────────────────────────────────────
        print(f"\nCreating circles…")
        r = await client.get(f"{api_url}/circles", headers=headers)
        existing_circles = {c["name"]: c["id"] for c in (r.json() if r.status_code == 200 else [])}

        for spec in TEST_ORG_CIRCLES:
            if spec["name"] in existing_circles:
                print(f"  Circle '{spec['name']}' exists")
                continue
            # Circles are created via motions in full PAAS — but in bootstrap
            # the org router allows direct creation
            # Try org API first, then skip gracefully
            r = await client.post(f"{api_url}/org/circles", headers=headers, json={
                "name": spec["name"],
                "description": f"Simulation circle for {', '.join(spec['dormains'])} domain(s).",
                "dormain_ids": [dormain_map[d] for d in spec["dormains"] if d in dormain_map],
            })
            if r.status_code in (200, 201):
                print(f"  ✓ Circle: {spec['name']}")
            else:
                # POST /org/circles may not exist — that's OK, agents can participate without
                print(f"  NOTE: circle '{spec['name']}' creation returned {r.status_code} "
                      f"(circles may need to be created via governance motions)")

        # ── 6. Summary ───────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"  Test org ready")
        print(f"{'='*60}")
        print(f"  Org slug:         {TEST_ORG_SLUG}")
        print(f"  Founder:          @{FOUNDER_HANDLE} / {FOUNDER_PASSWORD}")
        print(f"  Dormains:         {len(dormain_map)}")
        print(f"  Bootstrap state:  open (agents self-register via POST /auth/register)")
        print(f"{'='*60}")
        print(f"\nDormain IDs (save these):")
        for name, did in dormain_map.items():
            print(f"  {name}: {did}")

        # Save dormain map for runner
        with open("dormain_map.json", "w") as f:
            json.dump(dormain_map, f, indent=2)
        print(f"\n  Saved to dormain_map.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Orb Sys test org")
    parser.add_argument("--api",   default=API_URL, help="API base URL")
    parser.add_argument("--force", action="store_true", help="Force recreate")
    args = parser.parse_args()
    asyncio.run(setup(args.api, args.force))


if __name__ == "__main__":
    main()
