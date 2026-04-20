# Orb Sys

A full-stack implementation of the **Polycentric Autonomy-Audit System (PAAS)** —
a governance framework for fluid, trust-sparse organisations.

## Stack

| Layer | Technology |
|---|---|
| API | Python 3.12 · FastAPI · SQLAlchemy 2.x async |
| Database | PostgreSQL 16 · Alembic migrations |
| Events | NATS JetStream |
| Engines | Integrity · Inferential · Insight (Python asyncio) |
| Blind Review | Isolated FastAPI service (port 8001) |
| Frontend | Next.js 15 · React · Tailwind CSS |

## Quick start

```bash
cd infra
docker compose up -d

# Run all three migrations
docker compose exec api alembic upgrade head

# Seed: org + circles + founder + 3 demo threads + bootstrap complete
docker compose exec api python -m src.scripts.seed

# Open
open http://localhost:3000
# Login: handle=founder / password=change-me-2025
```

API docs: http://localhost:8000/docs  
Blind Review API: http://localhost:8001 (no /docs — by design)

## Architecture

```
apps/
  api/          FastAPI backend — 69 routes across 10 domains
  blind/        Blind Review API — structurally isolated, no reviewer_id column
  web/          Next.js 15 frontend — 18 pages

services/
  integrity/    Ledger · ΔC computation · resolution enactment · anomaly detection
  inferential/  STF candidate matching · dormain tagging · feed scoring
  insight/      Draft generation · minutes · notifications · deadline monitoring

tests/
  agents/       Standalone HTTP-only agent simulation engine
                Scenarios: normal · sybil · capture · collusion · mixed · stress
```

## Governance lifecycle

```
Commons thread
  → sponsor (Circle member with mandate)
    → Deliberation Cell
      → Cell contributions + competence-weighted vote
        → Crystallise → file motion (non_system | sys_bound | hybrid)
          → Gate 1 aSTF (blind parallel review)
            → [approve] → Resolution created → implementing circle executes
              → Gate 2 (diff for sys_bound, interpretive for non_system)
                → enacted_locked
            → [revision_request] → Cell reactivates
            → [reject] → Cell dissolved, public report
```

## Member join flow

Post-bootstrap: `POST /members/apply` → Membership Circle reviews → approve creates Member account.

Membership policy is governed by the `membership_policy` org parameter:
- `open_application` — anyone can apply, Membership Circle reviews
- `invite_only` — must be invited by a Circle member
- `closed` — no new members

## Agent simulation

```bash
cd tests/agents
pip install -e .
python setup.py          # provision paas-sim org
python runner.py --scenario normal   --agents 50  --duration 300
python runner.py --scenario sybil    --agents 200 --duration 600 --report results.json
python runner.py --scenario all      --agents 80  --duration 240 --report all.json
```

Requires `ANTHROPIC_API_KEY` for LLM-powered agent decisions. Falls back to rule-based without it.

## Migrations

| Migration | Contents |
|---|---|
| 0001 | Full schema — 32 tables |
| 0002 | `notifications` · `feed_scores` |
| 0003 | `member_applications` |

## Key design invariants

- **STF blind review**: `stf_verdicts` has no `reviewer_id` column — identity absence is structural
- **`implementing_circle_ids`**: required at filing for `non_system` / `hybrid` motions (Pydantic + service layer)
- **Ledger**: append-only · SHA-256 hash chain · verified at `GET /ledger/verify`
- **Integrity Engine**: sole writer for competence, ledger, and system parameter writes
- **Token incompatibility**: isolated_view tokens → 403 on main API (not 401)
- **Bootstrap**: `POST /org/bootstrap-complete` sets `bootstrapped_at`, dissolves founding circle, seeds `membership_policy`
