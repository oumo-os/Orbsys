# Orb Sys

**A governance platform implementing the Polycentric Autonomy-Audit System (PAAS).**

Orb Sys is a full-stack sociotechnical governance engine for organisations that
need legitimate, meritocratic decision-making without hierarchical authority. It
implements the complete PAAS specification: competence-weighted deliberation,
structured governance workflows, independent STF auditing, and a
cryptographically verifiable ledger of every governance action.

---

## Table of Contents

- [What this is](#what-this-is)
- [Quick start](#quick-start)
- [Architecture](#architecture)
- [Repository structure](#repository-structure)
- [Environment variables](#environment-variables)
- [Make targets](#make-targets)
- [Implementation status](#implementation-status)
- [Specification documents](#specification-documents)

---

## What this is

Orb Sys translates the PAAS governance model into a running application. Four
foundational design commitments:

**Competence governs, not position.** Every vote is weighted by a member's
demonstrated expertise (W_s) in the relevant Dormain. W_s is earned through
formal peer review, not assigned by administrators. The ΔC formula is
`G · K · Σ[(S_r − 0.5) · w_r,d · M_r,d] / Σ[w_r,d · M_r,d]`.

**Audits are structurally independent.** Short-Term Facilitators (STFs) are
commissioned and matched by an engine, not self-selected. Blind review types
(aSTF, vSTF, jSTF) have identity sealed at the database layer — `stf_verdicts`
has no `reviewer_id` column. This is structural absence, not a permission flag.

**The ledger is tamper-evident and member-verifiable.** Every governance action
is a signed `SHA-256(prev_hash|event_id|event_type|subject_id|payload_json)`
hash-chain event. Any member can verify the full chain via `GET /ledger/verify`.

**Engines serve humans.** The three engine services (Inferential, Insight,
Integrity) route, draft, and compute — but every governance action requires a
human decision. No automated enactments.

---

## Quick start

```bash
# 1. Clone and enter
git clone <repo> && cd orbsys

# 2. Copy env
cp .env.example .env
# Edit JWT_SECRET_KEY — change from default before first use

# 3. Start infrastructure (postgres, nats, minio)
make infra

# 4. Wait ~10 seconds for postgres to be healthy, then:
make bootstrap
# Creates schema + seeds: org=meridian, handle=founder, password=change-me-2025

# 5. Open http://localhost:3000 and sign in
```

Or run everything in Docker:

```bash
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m src.scripts.seed
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs (dev) | http://localhost:8000/docs |
| Blind Review API | http://localhost:8001 |
| NATS monitoring | http://localhost:8222 |
| MinIO console | http://localhost:9001 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  apps/web          Next.js 15 frontend                          │
│  (port 3000)       TypeScript · Tailwind · Zustand              │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────────────────┐
│  apps/api          FastAPI — main API server                     │
│  (port 8000)       65 routes · SQLAlchemy async · JWT           │
│                    DB role: orbsys_app (SELECT + INSERT)         │
└──────┬──────────────────┬──────────────────────────────────────┘
       │ isolated         │ NATS JetStream events
       │ network          │ ORG.<org_id>.events
       │         ┌────────┼──────────────────────┐
       │         ▼        ▼                      ▼
       │  ┌──────────┐ ┌─────────┐  ┌──────────────────────┐
       │  │Inferential│ │ Insight │  │    Integrity         │
       │  │ Engine   │ │ Engine  │  │    Engine            │
       │  │(router / │ │(scribe /│  │ Single writer.       │
       │  │ matcher) │ │ drafter)│  │ Ledger + ΔC + enact  │
       │  │read-only │ │read-only│  │ orbsys_integrity role│
       │  └──────────┘ └─────────┘  └──────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│  apps/blind        Blind Review API                              │
│  (port 8001)       X-Isolated-View-Token only                   │
│                    stf_verdicts has no reviewer_id column        │
│                    DB role: orbsys_blind                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  infra/postgres    PostgreSQL 16                                 │
│  (port 5432)       5 DB roles · append-only triggers            │
│                    RLS org isolation · hash chain               │
└─────────────────────────────────────────────────────────────────┘
```

### Token types

Two token types are structurally incompatible:

| Type | Claim `type` | Accepted by | Contains |
|---|---|---|---|
| Session | `"access"` | `apps/api` only | `member_id`, `org_id`, `state` |
| Isolated view | `"isolated_view"` | `apps/blind` only | `stf_instance_id`, `assignment_id` |

Session tokens sent to the blind endpoint receive `403 TOKEN_TYPE_MISMATCH`,
not 401. The wrong token type is an access control failure, not an auth failure.

---

## Repository structure

```
orbsys/
├── .env.example
├── Makefile
├── README.md
├── TECHNICAL.md                    ← implementation reference
│
├── docs/                           ← full specification corpus
│   ├── OrbSys_v7.md                ← governance architecture spec
│   ├── OrbSys_engines_v2.md        ← engine trinity formulas + behaviour
│   ├── OrbSys_bootstrap_v2.md      ← org bootstrapping sequence
│   ├── TECHNICAL.md                ← implementation guide
│   ├── Issue_Lifecycle__The_Forked_Path.mermaid
│   ├── PAAS_Efficiency_Analysis__Small_Teams__Massive_Output.md
│   ├── Crisis_Scenario_Comparisons__Governance_Under_Stress.md
│   ├── Multi-Dimensional_Governance_Radar_Charts.md
│   ├── paas-v2.jsx                 ← interactive governance prototype
│   └── A_Polycentric_Autonomy-Audit_System_Reviewed_14-12-2025_2-1.pdf
│
├── apps/
│   ├── api/                        ← main API server (FastAPI, port 8000)
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── pyproject.toml
│   │   ├── alembic/
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   │       └── 0001_initial_schema.py   ← full schema + triggers
│   │   └── src/
│   │       ├── main.py             ← app, router registration, CORS
│   │       ├── core/
│   │       │   ├── config.py       ← pydantic-settings
│   │       │   ├── database.py     ← async SQLAlchemy engine
│   │       │   ├── dependencies.py ← ActiveMember, GovWriter, BlindCtx, DB
│   │       │   ├── events.py       ← EventBus, GovernanceEvent, EventType enum
│   │       │   ├── exceptions.py   ← OrbSysError hierarchy
│   │       │   └── security.py     ← JWT, password, token creation
│   │       ├── models/
│   │       │   ├── types.py        ← all enums + column helpers
│   │       │   ├── org.py          ← Org, Member, Dormain, Circle, CircleMember
│   │       │   ├── competence.py   ← CompetenceScore, Curiosity, DeltaCEvent, WhCredential
│   │       │   └── governance.py   ← Commons, Cell, Motion, Resolution, STF, Ledger
│   │       ├── schemas/            ← Pydantic request/response schemas (all domains)
│   │       │   ├── auth.py · org.py · members.py · competence.py
│   │       │   ├── commons.py · cells.py · motions.py · circles.py
│   │       │   ├── stf.py · ledger.py · common.py
│   │       │   └── __init__.py     ← central export
│   │       ├── services/           ← business logic (one file per domain)
│   │       │   ├── auth.py · org.py · members.py · competence.py · commons.py
│   │       │   ├── cells.py · motions.py · circles.py · stf.py · ledger.py
│   │       │   └── base.py         ← BaseService (get_by_id, save)
│   │       ├── routers/            ← FastAPI routes (thin, call services)
│   │       │   ├── auth.py · org.py · members.py · competence.py · commons.py
│   │       │   ├── cells.py · motions.py · circles.py · stf.py · ledger.py
│   │       │   └── __init__.py
│   │       └── scripts/
│   │           └── seed.py         ← bootstrap: org + dormains + circles + founder
│   │
│   ├── blind/                      ← Blind Review API (isolated, port 8001)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/main.py             ← GET /blind/:id/content, POST /blind/:id/verdicts
│   │
│   └── web/                        ← Next.js 15 frontend (port 3000)
│       ├── Dockerfile
│       ├── package.json
│       ├── tailwind.config.ts
│       ├── next.config.ts          ← standalone output for Docker
│       └── src/
│           ├── app/
│           │   ├── layout.tsx · page.tsx · globals.css
│           │   ├── auth/login/page.tsx
│           │   └── org/
│           │       ├── layout.tsx          ← auth guard + sidebar nav
│           │       ├── commons/page.tsx    ← thread feed + create
│           │       ├── commons/[id]/page.tsx ← thread detail + posts + formal review
│           │       ├── competence/page.tsx ← W_s scores by dormain
│           │       ├── circles/page.tsx
│           │       ├── stf/page.tsx
│           │       ├── members/page.tsx    ← profile + activity feed
│           │       ├── cells/page.tsx      ← stub
│           │       └── motions/page.tsx    ← stub
│           ├── lib/api.ts           ← typed axios client (all endpoints)
│           ├── middleware.ts        ← Next.js auth guard
│           ├── stores/auth.ts       ← Zustand: member, tokens, hydration
│           └── types/index.ts
│
├── services/
│   ├── integrity/                  ← Integrity Engine
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/main.py             ← full: ΔC, W_h boost, gate1, enactment
│   │
│   ├── inferential/                ← Inferential Engine
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── src/main.py             ← routing, tagging, matching stubs
│   │
│   └── insight/                    ← Insight Engine
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── src/main.py             ← draft gen, notifications stubs
│
└── infra/
    ├── docker-compose.yml          ← full stack (api, blind, 3 engines, web, pg, nats, minio)
    └── postgres/
        └── init.sql                ← roles, extensions, enforce_append_only()
```

---

## Environment variables

See `.env.example` for all variables. Critical ones:

| Variable | Notes |
|---|---|
| `JWT_SECRET_KEY` | **Change before first use.** Signs all tokens. |
| `DATABASE_URL` | Main API connection — `orbsys_app` role |
| `DATABASE_URL_INTEGRITY` | Integrity Engine — `orbsys_integrity` role (exclusive writer) |
| `DATABASE_URL_BLIND` | Blind API — `orbsys_blind` role (narrow grants) |
| `NATS_URL` | Event bus |
| `LLM_API_KEY` | Insight Engine — required only if using LLM draft features |

DB role boundaries are security boundaries, not conventions. Each service
connects with a different role. The `orbsys_blind` role has `SELECT` on
`stf_assignments` and `INSERT` on `stf_verdicts` — nothing more.

---

## Make targets

```
make infra         Start postgres, nats, minio in Docker
make up            Start full stack in Docker
make dev           Start all services locally (infra in Docker)
make bootstrap     First run: migrate + seed [ORG=x HANDLE=x PASSWORD=x]
make migrate       Run pending Alembic migrations
make migration MSG="..." Generate new migration from models
make seed          Load seed data (idempotent)
make status        Quick health check on all services
make logs          Follow logs (api, blind, integrity)
make lint          ruff check
make fmt           ruff format
make test          pytest
make clean         Remove __pycache__
```

---

## Implementation status

All 65 API routes are wired and return correct HTTP semantics (no 501 stubs).
The service layer is complete for all domains.

**Fully implemented:**
- Auth: login, refresh, bootstrap registration
- Org: creation, dormain management, parameter reads
- Members: profile, feed (chronological fallback), curiosities
- Commons: threads, posts, dormain tagging, formal review, sponsorship draft
- Cells: contributions, competence-weighted votes, crystallise, file-motion
- Motions: reads, specification dry-run validation
- Circles: list, get, members, invitation (bootstrap auto-confirm)
- STF: commission, assignments (identity-safe), verdicts, enact (NATS request/reply)
- Competence: W_s scores, leaderboard, W_h claim submission
- Ledger: event reads, hash-chain verification, audit archive
- Blind Review API: isolated token auth, content reads, verdict filing
- Integrity Engine: ΔC, W_h boost, gate1 result, STF completion, resolution enactment
- Database: 32 tables, append-only triggers, 5 role model, hash chain

**Deferred to v1.1:**
- NATS request/reply for Insight Engine crystallise draft (currently returns stub)
- Inferential Engine NLP dormain tagger (currently author-signal only)
- `feed_scores` and `notifications` tables (feed is chronological fallback)
- Endorsement provenance weighting in ΔC
- Transfer coefficients between Dormains
- Server-side JWT revocation

---

## Specification documents

All specification documents are in `docs/`. The academic paper is the
foundational reference; the implementation specs define exact behaviour.

| Document | Description |
|---|---|
| `docs/A_Polycentric_Autonomy-Audit_System_Reviewed_14-12-2025_2-1.pdf` | Academic paper — full PAAS theory and rationale |
| `docs/OrbSys_v7.md` | Implementation specification — screens, flows, governance logic |
| `docs/OrbSys_engines_v2.md` | Engine trinity — formulas, constraints, HCAI mandate |
| `docs/OrbSys_bootstrap_v2.md` | Bootstrap sequence — how an org comes into existence |
| `docs/TECHNICAL.md` | Technical reference — DB design, auth model, sharp edges |
| `docs/Issue_Lifecycle__The_Forked_Path.mermaid` | Issue lifecycle diagram |
| `docs/PAAS_Efficiency_Analysis__Small_Teams__Massive_Output.md` | Efficiency analysis |
| `docs/Crisis_Scenario_Comparisons__Governance_Under_Stress.md` | Crisis resilience analysis |
| `docs/Multi-Dimensional_Governance_Radar_Charts.md` | Governance system comparison |
| `docs/paas-v2.jsx` | Interactive UI prototype (React) |

When the code conflicts with the spec, the spec wins.
