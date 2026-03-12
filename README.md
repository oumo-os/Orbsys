# Orb Sys

**A governance platform implementing the Polycentric Autonomy-Audit System [(PAAS)](https://www.doi.org/10.13140/RG.2.2.17443.52000).**

Orb Sys is a sociotechnical governance engine for organisations that need
legitimate, meritocratic decision-making without hierarchical authority. It
implements the full PAAS specification: competence-weighted deliberation,
structured deliberation workflows, independent STF auditing, and a
cryptographically verifiable ledger of all governance actions.

---

## Table of Contents

- [What this is](#what-this-is)
- [Architecture overview](#architecture-overview)
- [Repository structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Getting started](#getting-started)
- [Development workflow](#development-workflow)
- [Environment variables](#environment-variables)
- [Useful make targets](#useful-make-targets)
- [Where things are not yet implemented](#where-things-are-not-yet-implemented)
- [Specification documents](#specification-documents)

---

## What this is

Orb Sys translates the PAAS governance model into a working application. The
core design commitments:

**Competence governs, not position.** Every vote is weighted by a member's
demonstrated expertise (W_s) in the relevant Dormain. W_s is earned through
formal peer review, not assigned by administrators.

**Audits are structurally independent.** Short-Term Facilitators (STFs) are
commissioned and matched by an engine, not self-selected. Blind review types
(aSTF, vSTF, jSTF) have identity sealed at the database layer — not a
permission flag, a structural absence in the schema.

**The ledger is tamper-evident and member-verifiable.** Every governance
action is a signed hash-chain event. Any member can verify the chain via
`GET /ledger/verify`. This is not a compliance feature — it is the trust
foundation of the entire system.

**Engines serve humans, not the reverse.** The three engine services
(Inferential, Insight, Integrity) route, draft, and compute — but every
governance action requires a human decision. No automated enactments.
No proactive drafts.

---

## Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│  apps/web          Next.js 15 — React frontend                  │
│  (port 3000)       TypeScript, Tailwind, Zustand, React Query   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────────┐
│  apps/api          FastAPI — main API server                     │
│  (port 8000)       Python 3.12, SQLAlchemy async, JWT auth      │
│                    DB role: orbsys_app (SELECT + INSERT)         │
└──────┬─────────────────────┬───────────────────────────────────┘
       │                     │ events
       │              ┌──────▼──────────────────────────────────┐
       │              │  infra/nats    NATS JetStream event bus  │
       │              │  Stream: ORG.<org_id>.events             │
       │              └──────┬──────────────────────────────────┘
       │                     │ consumed by all three engines
       │        ┌────────────┼────────────────────┐
       │        ▼            ▼                    ▼
       │  ┌───────────┐ ┌──────────┐  ┌──────────────────────┐
       │  │Inferential│ │ Insight  │  │    Integrity         │
       │  │  Engine   │ │ Engine   │  │    Engine            │
       │  │(router/   │ │(scribe/  │  │(ledger / locksmith)  │
       │  │ matcher)  │ │ drafter) │  │Single writer per org │
       │  │orbsys_    │ │orbsys_   │  │DB role: orbsys_      │
       │  │inferential│ │insight   │  │integrity             │
       │  │(read-only)│ │(read-only│  │(full write access)   │
       │  └───────────┘ └──────────┘  └──────────────────────┘
       │
       │ isolated network
┌──────▼──────────────────────────────────────────────────────────┐
│  apps/blind        FastAPI — Blind Review API                    │
│  (port 8001)       X-Isolated-View-Token only                   │
│                    No session JWT accepted                       │
│                    DB role: orbsys_blind                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  infra/postgres    PostgreSQL 16                                 │
│  (port 5432)       5 DB roles, append-only triggers,            │
│                    RLS for org isolation, hash chain enforcement │
└─────────────────────────────────────────────────────────────────┘
```

**The blind review isolation is structural, not a permission system.**
`stf_verdicts` has no `reviewer_id` column. Identity lives only in
`stf_assignments.member_id`, which is readable only by `orbsys_integrity`.
The two tables cannot be joined by any code path outside the Integrity Engine.

---

## Repository structure

```
orbsys/
├── .env.example                  — all required environment variables
├── Makefile                      — development commands
│
├── apps/
│   ├── api/                      — main API server (FastAPI)
│   │   ├── alembic/              — database migrations
│   │   │   └── env.py
│   │   ├── src/
│   │   │   ├── core/
│   │   │   │   ├── config.py     — settings (pydantic-settings)
│   │   │   │   ├── database.py   — async SQLAlchemy engine + session
│   │   │   │   ├── dependencies.py — FastAPI auth dependencies
│   │   │   │   └── security.py   — JWT, password, token types
│   │   │   ├── models/
│   │   │   │   ├── types.py      — all enums + column helpers
│   │   │   │   ├── org.py        — Org, Member, Dormain, Circle hierarchy
│   │   │   │   ├── competence.py — CompetenceScore, Curiosity, ΔC, W_h
│   │   │   │   └── governance.py — Commons, Cells, Motions, STF, Ledger
│   │   │   ├── routers/          — one router per domain (all stubbed)
│   │   │   │   ├── auth.py
│   │   │   │   ├── members.py
│   │   │   │   ├── competence.py
│   │   │   │   ├── commons.py
│   │   │   │   ├── cells.py
│   │   │   │   ├── motions.py
│   │   │   │   ├── stf.py
│   │   │   │   ├── circles.py
│   │   │   │   ├── org.py
│   │   │   │   └── ledger.py
│   │   │   ├── schemas/          — Pydantic request/response schemas (pending)
│   │   │   ├── services/         — business logic layer (pending)
│   │   │   ├── engines/          — engine client adapters (pending)
│   │   │   └── main.py           — FastAPI app, router registration
│   │   ├── alembic.ini
│   │   └── pyproject.toml
│   │
│   ├── blind/                    — Blind Review API (isolated service)
│   │   └── src/main.py
│   │
│   └── web/                      — Next.js 15 frontend
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx    — root layout, design tokens
│       │   │   ├── page.tsx      — redirect to /auth/login
│       │   │   ├── globals.css   — design system + CSS variables
│       │   │   ├── auth/login/
│       │   │   └── org/          — sidebar layout + section pages
│       │   │       ├── layout.tsx
│       │   │       ├── commons/
│       │   │       ├── cells/
│       │   │       ├── motions/
│       │   │       ├── stf/
│       │   │       ├── circles/
│       │   │       └── members/
│       │   ├── lib/
│       │   │   └── api.ts        — typed axios client for all endpoints
│       │   ├── stores/
│       │   │   └── auth.ts       — Zustand auth store
│       │   └── types/
│       │       └── index.ts      — all shared TypeScript types
│       ├── package.json
│       ├── tailwind.config.ts
│       └── next.config.ts
│
├── services/
│   ├── integrity/src/main.py     — ledger writer, ΔC computation, anomaly detection
│   ├── inferential/src/main.py   — routing, matching, dormain tagging
│   └── insight/src/main.py       — draft generation, notifications, minutes
│
└── infra/
    ├── docker-compose.yml        — full local stack
    └── postgres/
        └── init.sql              — roles, extensions, append-only function
```

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | Via `uv` recommended |
| uv | latest | `pip install uv` or `brew install uv` |
| Node.js | 20+ | |
| pnpm | 9+ | `npm install -g pnpm` |
| Docker | 24+ | For local infrastructure |
| Docker Compose | v2 | Bundled with Docker Desktop |

---

## Getting started

```bash
# 1. Clone and enter
git clone <repo>
cd orbsys

# 2. Copy env
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET_KEY to something real

# 3. Install dependencies
make install

# 4. Start infrastructure (postgres, nats, minio)
make infra

# 5. Run database migrations
make migrate

# 6. Start all services
make dev
```

Services will be available at:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs (dev only) | http://localhost:8000/docs |
| Blind Review API | http://localhost:8001 |
| NATS monitoring | http://localhost:8222 |
| MinIO console | http://localhost:9001 |

---

## Development workflow

### Adding a new migration

```bash
make migration MSG="add circle health snapshots"
# Then review the generated file in apps/api/alembic/versions/
make migrate
```

### Implementing a router endpoint

Endpoints are stubbed — they raise `HTTP 501 Not Implemented`. The
implementation order is:

1. Add Pydantic schemas to `apps/api/src/schemas/`
2. Add business logic to `apps/api/src/services/`
3. Update the router to call the service
4. Write a test in `apps/api/tests/`

The router signature and auth dependency are already set. Do not change
endpoint paths or auth requirements without updating `apps/web/src/lib/api.ts`
and this document.

### Running a single service

```bash
# API only (infra must be running)
cd apps/api && uv run uvicorn src.main:app --reload --port 8000

# Frontend only
cd apps/web && pnpm dev

# Single engine
cd services/integrity && uv run python -m src.main
```

### Tests

```bash
make test          # all
cd apps/api && uv run pytest tests/ -v -k "test_auth"   # filtered
```

---

## Environment variables

All variables are documented in `.env.example`. Key ones:

| Variable | Purpose | Required |
|---|---|---|
| `JWT_SECRET_KEY` | Signs all tokens | Yes — change from default |
| `DATABASE_URL` | Main API DB connection | Yes |
| `DATABASE_URL_INTEGRITY` | Integrity Engine exclusive connection | Yes |
| `NATS_URL` | Event bus | Yes |
| `LLM_API_KEY` | Insight Engine LLM calls | Only if using LLM features |

**Token types use separate DB roles with different access.** Do not use
`DATABASE_URL` for engine services — they have their own connection strings
that enforce the correct DB role. The role boundaries are security boundaries,
not conventions.

---

## Useful make targets

```
make infra         Start postgres, nats, minio in Docker
make dev           Start all services locally (infra in Docker)
make migrate       Run all pending Alembic migrations
make migration MSG="..." Generate a new migration
make seed          Load development seed data
make lint          Run ruff (Python) + eslint (TypeScript)
make fmt           Run ruff format + prettier
make test          Run all test suites
make install       Install all dependencies (uv + pnpm)
make logs SERVICE=api  Follow Docker logs for a service
```

---

## Where things are not yet implemented

Every router endpoint currently raises `HTTP 501 Not Implemented`. The
scaffold is the shape — implementation fills it in.

**Immediate next layer (in order):**

1. **Database migrations** — `alembic revision --autogenerate` from the
   existing models will produce the full schema. All tables, enums, and
   append-only triggers need to be reviewed and applied.

2. **Auth + member registration** — `POST /auth/login`, `POST /org`,
   member invite flow. This unblocks everything downstream.

3. **Pydantic schemas** — request/response bodies for all routes.
   `apps/api/src/schemas/` is empty. One schema file per domain to match
   the router structure.

4. **Service layer** — `apps/api/src/services/` is empty. Business logic
   lives here, not in routers. Routers call services, services call models.

5. **Integrity Engine** — `services/integrity/src/main.py` has the ΔC
   formula and event handler stubs. The NATS consumer is wired. Needs DB
   writes and the hash chain implementation.

6. **Inferential Engine** — Dormain tagging NLP, STF candidate scoring,
   feed relevance. DB reads only — no writes.

7. **Frontend pages** — Stubs exist for all 6 sections. Commons feed and
   the deliberation Cell view are the highest-priority UX surfaces.

**Known deferred items (v1.1):**

- Endorsement provenance weighting in ΔC
- Transfer coefficients between Dormains
- Voluntary STF identity disclosure
- Token-based revocation (currently stateless JWT, no server-side revocation)
- Blockchain ledger backend option (EventStoreDB / Hyperledger)

---

## Specification documents

The full governance specification lives alongside the codebase. These are
the authoritative source for any implementation question:

| Document | Contents |
|---|---|
| `OrbSys_v7.md` | Governance architecture — the full PAAS spec |
| `OrbSys_engines_v2.md` | Engine trinity — formulas, behaviours, constraints |
| `OrbSys_datamodel_v1.md` | Full data model with all tables and design decisions |
| `OrbSys_api_v1.md` | API surface — auth model, endpoints, token types |
| `OrbSys_deployment_v1.md` | Deployment architecture — tiers, failure modes |
| `OrbSys_bootstrap_v2.md` | Bootstrap flow — how an org comes into existence |
| `OrbSys_simulation_v1.md` | Agent-based simulation parameters — pre-deployment testing |

When in doubt, the spec takes precedence over the code. The code is an
implementation of the spec, not the other way around.
