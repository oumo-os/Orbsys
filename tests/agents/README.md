# Orb Sys — Agent Simulation Engine

A **standalone simulation harness** that sits entirely outside the Orb Sys
monorepo services. It speaks only HTTP to the running API — no shared code,
no DB access, no event bus access.

## What it tests

**PAAS paper validation** — Does meritocracy actually emerge? Does the
autonomy-audit loop hold under adversarial conditions? Do competence scores
accurately reflect contribution quality?

**Governance stress testing** — Capture attempts, Sybil floods, coordinated
endorsement rings, dormain-based plutocracy, aSTF bypass patterns.

**Load / concurrency** — Hundreds of concurrent agents, thousands over time.
The system should handle this gracefully and the Inferential Engine's anomaly
detection should surface the adversarial patterns.

## Architecture

```
tests/agents/
  setup.py          Provision test org + initial circles via API (run once)
  runner.py         Scenario orchestrator — spawns, batches, paces agents
  factory.py        LLM-powered dynamic agent generation (profiles + behaviour)
  agent.py          Individual agent — LLM-powered decisions and content
  client.py         HTTP-only API client (no DB access, no shared imports)
  scenarios/
    normal.py       Healthy governance: diverse participation, genuine deliberation
    sybil.py        Identity flooding: many low-competence bots push one agenda
    capture.py      Circle capture: coordinated nominations to stack a circle
    collusion.py    Endorsement rings: coordinated W_s inflation attempts
    stress.py       Concurrent load: hundreds of simultaneous active agents
  metrics.py        Scenario outcome analysis — what did the system do?
  config.py         Environment-driven configuration
```

## Setup

### 1. Start Orb Sys

```bash
cd orbsys/infra
docker compose up -d
docker compose exec api alembic upgrade head
```

### 2. Provision test org (once)

```bash
cd tests/agents
pip install -e .
python setup.py
```

Creates `paas-sim` org in bootstrap state (bootstrapped_at=null), which keeps
self-registration permanently open. Agents self-register as they're spawned.
No special access needed — just the public API.

### 3. Run a scenario

```bash
# Healthy governance baseline
python runner.py --scenario normal --agents 50 --duration 300

# Sybil attack simulation
python runner.py --scenario sybil --agents 200 --duration 600 --report

# Full stress test
python runner.py --scenario stress --agents 500 --concurrent 100

# All scenarios in sequence
python runner.py --scenario all --report metrics.json
```

### Environment

| Variable | Description | Default |
|---|---|---|
| `API_URL` | Orb Sys API base URL | `http://localhost:8000` |
| `BLIND_API_URL` | Blind Review API URL | `http://localhost:8001` |
| `TEST_ORG_SLUG` | Test org slug | `paas-sim` |
| `ANTHROPIC_API_KEY` | For LLM-powered agents | (falls back to rule-based) |
| `AGENT_CONCURRENCY` | Max simultaneous active agents | `50` |
| `RATE_LIMIT` | Max API req/s per agent | `2.0` |

## Test org design

The `paas-sim` org stays in bootstrap state permanently. This means:
- `POST /auth/register?org_slug=paas-sim` works for any new agent
- Agents self-register with LLM-generated identities
- No circle invite needed for bootstrap members (auto-confirmed)
- Each scenario starts with a clean agent roster (or reuses existing ones)
- The test org is completely isolated from `meridian`

## LLM-powered agent decisions

Each agent has an LLM-generated persona (background story, expertise domain,
personality, and optionally a hidden agenda). During their activity loop the
agent passes the current system state to Claude and asks: "Given your persona
and what you see, what would you do next and what would you write?"

Without `ANTHROPIC_API_KEY` set, agents fall back to rule-based behaviour —
still exercising all API paths but with less realistic content.

## Security test scenarios

**Sybil** — 200 bots all share the same hidden agenda. They try to push the
same motion through by flooding the deliberation with supportive posts and
coordinated votes. Expected: Integrity Engine flags the correlation; aSTF
catches the thin deliberation quality; W_s stays low because they endorse
only each other (low reviewer W_s × low M_cmp).

**Capture** — 30 coordinated bots systematically build W_s in one dormain,
then all volunteer for the same circle. Expected: Inferential Engine homogeneity
warning; aSTF composition balancer brings in independent reviewers.

**Collusion ring** — 20 bots form a mutual-endorsement network. Expected:
Endorser meta-reputation tracking reduces their effective M; rate limits on
endorsements trigger; pattern detection flags to jSTF.
