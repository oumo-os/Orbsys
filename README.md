# Orb Sys

A production-quality implementation of the **Polycentric Autonomy-Audit System (PAAS)** — a socio-technical governance framework for fluid, trust-sparse organisations.

---

## Architecture

```
orbsys/
├── apps/
│   ├── api/          FastAPI backend  (port 8000)
│   ├── blind/        Blind Review API (port 8001) — STF reviewer isolation
│   └── web/          Next.js 15 frontend (port 3000)
├── services/
│   ├── integrity/    Integrity Engine  — ledger writer, ΔC, system writes
│   ├── inferential/  Inferential Engine — feed scoring, STF matching, tagging
│   └── insight/      Insight Engine    — LLM drafts, notifications, minutes
└── infra/
    ├── docker-compose.yml
    └── postgres/init.sql   — roles, extensions, append-only triggers
```

### Key design principles

| Principle | Implementation |
|---|---|
| Competence-weighted voting | W_s (soft) × M_cmp per dormain; governed by the ΔC formula |
| Blind review | `stf_verdicts` has no `reviewer_id` column — identity cannot leak from the API |
| Append-only ledger | Postgres triggers on all governance tables; SHA-256 hash chain |
| Integrity Engine as sole writer | Only `orbsys_integrity` DB role can write competence + ledger |
| NATS request/reply | Crystallise and sponsor-draft use request/reply; STF formation is async |
| Token incompatibility | `isolated_view` tokens rejected by main API (403 not 401) |

---

## First run

### Prerequisites
- Docker + Docker Compose v2
- 4 GB RAM available

### Start the stack

```bash
cd orbsys/infra
docker compose up -d
```

Wait for all services to be healthy (~30s):

```bash
docker compose ps
```

### Run migrations

```bash
docker compose exec api alembic upgrade head
```

Applies:
- `0001_initial_schema` — 32 tables, 5 DB roles, append-only triggers, hash chain
- `0002_notifications_feed_scores` — notifications and feed_scores tables

### Seed demo data

```bash
docker compose exec api python -m src.scripts.seed
```

Creates:
- Org: **Meridian Collective** (slug: `meridian`)
- 6 dormains: Governance, Protocol Engineering, Community, Security, Treasury, Research
- 6 circles, all seeded with the founding member
- 3 demo Commons threads for walking the governance lifecycle

**Credentials:** `@founder` / `change-me-2025`

### Open the app

| URL | Service |
|---|---|
| http://localhost:3000 | Frontend |
| http://localhost:8000/docs | API (Swagger) |
| http://localhost:8001/docs | Blind Review API |
| http://localhost:8222 | NATS monitoring |

---

## Walking the governance lifecycle

After seeding, the fastest path through the full loop:

1. **Login** at http://localhost:3000 — `meridian` / `founder` / `change-me-2025`
2. **Commons** → open a thread → click **Sponsor** to generate a Cell
3. **Cells** → open the new Cell → add contributions → click **Crystallise** (Insight Engine draft)
4. **File motion** from the crystallise modal → switch to **Vote** tab → cast a vote
5. The aSTF is auto-commissioned by the Inferential Engine
6. **STF** → open the aSTF → click **Review →** (loads blind review page)
7. Enter the isolated view token (from STF assignments) → file verdict
8. Once all verdicts filed: **Enact resolution** (triggers Integrity Engine atomic write)
9. **Ledger** → verify chain integrity → view audit archive

---

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|---|---|---|
| `JWT_SECRET_KEY` | **Change for production** | `dev-secret-change-in-production` |
| `DATABASE_URL` | PostgreSQL async URL | `localhost:5432/orbsys` |
| `NATS_URL` | NATS JetStream URL | `nats://localhost:4222` |
| `LLM_BACKEND` | `openai` \| `anthropic` \| `local` | `local` |
| `LLM_API_KEY` | API key for LLM backend | (empty = local fallback) |
| `LLM_MODEL` | Model identifier | `gpt-4o` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `NEXT_PUBLIC_BLIND_API_URL` | Blind Review API URL (browser-facing) | `http://localhost:8001` |

Without an LLM key the Insight Engine falls back to rule-based extraction for crystallise drafts and sponsor mandates — fully functional, less polished.

---

## Database roles

| Role | Access | Used by |
|---|---|---|
| `orbsys_migrations` | Schema owner | Alembic |
| `orbsys_app` | SELECT + INSERT on application tables | `apps/api` |
| `orbsys_blind` | Narrow SELECT on STF content, INSERT on verdicts | `apps/blind` |
| `orbsys_integrity` | Full access, exclusive ledger + competence writes | `services/integrity` |
| `orbsys_inferential` | SELECT only | `services/inferential` |
| `orbsys_insight` | SELECT only (RLS blocks blind cells) | `services/insight` |

---

## Development (no Docker)

```bash
# 1. Start infrastructure only
docker compose up -d postgres nats

# 2. API
cd apps/api
pip install -e ".[dev]"
alembic upgrade head
python -m src.scripts.seed
uvicorn src.main:app --reload --port 8000

# 3. Blind Review API
cd apps/blind
pip install -e .
uvicorn src.main:app --reload --port 8001

# 4. Engines (each in a separate terminal)
cd services/integrity && python src/main.py
cd services/inferential && python src/main.py
cd services/insight && python src/main.py

# 5. Frontend
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 \
NEXT_PUBLIC_BLIND_API_URL=http://localhost:8001 \
npm run dev
```

---

## ΔC formula (competence change)

```
ΔC_u,d = G · K_u,d · Σ[(S_r − 0.5) · w_r,d · M_r,d]
          ────────────────────────────────────────────
                      Σ[w_r,d · M_r,d]
```

| Symbol | Values |
|---|---|
| G (activity gravity) | 0.5 Commons · 1.0 Cell/motion · 1.2 audit |
| K (volatility) | 60 new · 30 established · 10 veteran |
| S_r (reviewer score) | 0.0–1.0 (centred at 0.5 = neutral) |
| M (circle multiplier) | 1.6 primary · 1.2 related · 1.0 unrelated |
| C_max | 120 pts per event |
| T_audit | 50 pts — held pending_audit if exceeded |

---

## Ledger hash chain

```
event_hash = SHA-256(prev_hash | event_id | event_type | subject_id | payload_json)
```

Verifiable by any member: `GET /ledger/verify`

Broken chain (any row modified) is detected at the first changed row and every subsequent one.

---

## Blind review token structure

```json
{
  "stf_instance_id": "<uuid>",
  "assignment_id": "<uuid>",
  "type": "isolated_view",
  "exp": <unix_timestamp>
}
```

- Accepted **only** by `apps/blind` on port 8001
- Session Bearer tokens return 403 (not 401) on the blind endpoint
- No `member_id` — reviewer identity is absent from the token
- Expires at STF deadline or 14 days, whichever is sooner

---

---

## Test Agent Engine

A set of bot personas that simulate live governance activity by calling the real API. Exercises the full stack — NATS events, ΔC computation, feed scoring, STF formation, blind review — without requiring human users.

### Personas

| Handle | Focus | Style |
|---|---|---|
| `@alice_proto` | Protocol Engineering, Security | Analytical |
| `@bob_governs` | Governance, Community | Deliberative |
| `@carol_research` | Research, Governance | Questioning |
| `@dave_sec` | Security, Protocol | Concise |
| `@eve_community` | Community, Governance | Deliberative |
| `@frank_treasury` | Treasury, Governance | Analytical |

### Setup

First create bot accounts (run once after initial seed):

```bash
docker compose exec api python -m src.scripts.seed --agents
```

### Run agents

```bash
# With Docker (opt-in profile)
docker compose --profile agents up agents

# Or directly
cd services/agents
pip install -e .
API_URL=http://localhost:8000 \
BLIND_API_URL=http://localhost:8001 \
ORG_SLUG=meridian \
CYCLE_INTERVAL=30 \
python src/main.py
```

### Configuration

| Variable | Description | Default |
|---|---|---|
| `CYCLE_INTERVAL` | Seconds between full activity cycles | `45` |
| `JITTER` | ±seconds of random timing per action | `8` |
| `AGENTS` | Comma-separated handles, or `all` | `all` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### What the bots do each cycle

- **Commons** — post replies to open threads, file formal reviews on other members' posts (generating ΔC), occasionally sponsor threads as Cells
- **Cells** — contribute to active deliberation cells, cast competence-weighted votes on open motions; cell initiator bots crystallise mature cells and file motions
- **STF verdicts** — file blind review verdicts via the isolated view token on the Blind Review API

The bots do not interact with each other directly — they independently respond to the system state, which creates emergent multi-party deliberation patterns.

---

## Known deferred items (v1.1)

- Endorsement provenance weighting in ΔC (field exists, not computed)
- W_s decay background job (formula implemented, scheduled trigger pending)
- Transfer coefficients between related dormains
- Server-side JWT revocation (currently stateless)
- NATS JetStream stream auto-creation on first boot
- Voluntary STF identity disclosure (governance option) — PAAS authorship discourages this

---

## Spec documents

Full academic paper, engine specs, bootstrapping flow, and implementation reference in `docs/`.
