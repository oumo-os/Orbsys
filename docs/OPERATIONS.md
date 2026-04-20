# Orb Sys — Operations Guide

> Day-to-day operating procedures: running scenarios, reading engine logs,
> interpreting Integrity Engine anomaly flags, and managing the governance system.

---

## Starting the stack

```bash
cd infra

# Start all services
docker compose up -d

# Check status
docker compose ps

# Run migrations (first time or after new migration files)
docker compose exec api alembic upgrade head

# Seed a demo org
docker compose exec api python -m src.scripts.seed

# Tail all logs
docker compose logs -f

# Tail a specific service
docker compose logs -f integrity
docker compose logs -f inferential
docker compose logs -f insight
```

### Service health checks

```bash
# API
curl http://localhost:8000/health
# → { "status": "ok", "db": "connected", "nats": "connected" }

# Chain integrity (authenticate first)
curl -H "Authorization: Bearer <token>" http://localhost:8000/ledger/verify
# → { "status": "ok", "verified_events": N, "first_broken_event_id": null }
```

---

## Engine logs

All three engines log to stdout with structured prefixes. When tailing:

```
[integrity] gate1 approve → motion=<uuid>
[integrity] STF <uuid> completed — majority: approve
[integrity] ΔC applied: member=<uuid> dormain=<name> delta=+24.3
[integrity] anomaly_flagged: TYPE=COMPETENCE_SPIKE subject=<uuid>

[inferential] STF <uuid>: 5 candidates scored, 3 assigned
[inferential] vSTF <uuid> commissioned for W_h claim <uuid>
[inferential] homogeneity flag: Cell <uuid> circles share 87% Dormain overlap
[inferential] error handling cell_created: <reason>  ← investigate immediately

[insight] crystallise draft generated for Cell <uuid>
[insight] STF deadline warning: <stf_uuid> expires in 22h
[insight] P2 daily cap hit for member <uuid>  ← normal, not an error
```

### What to watch for

**Errors (investigate immediately):**
- Any `[integrity] error in <event_type>:` — Integrity Engine errors may mean a
  failed DB write or NATS disconnect. Check `docker compose logs integrity` for
  the full traceback.
- `CHAIN_INTEGRITY_FAILURE` in `GET /ledger/verify` — the chain is broken.
  This should never happen in normal operation. See [Chain integrity](#chain-integrity).

**Warnings (review periodically):**
- `[integrity] anomaly_flagged` — the Integrity Engine detected a pattern worth
  human review. See [Interpreting anomaly flags](#interpreting-anomaly-flags).
- `[inferential] no candidates scored for STF` — the org doesn't have enough
  members with W_s in the relevant Dormain. Consider expanding the novice floor
  or recruiting members with that expertise.
- `[integrity] ΔC held pending_audit` — a single activity generated >50 ΔC.
  Normal for a new member receiving endorsements on strong work, but worth verifying.

**Info (normal):**
- `P2 daily/hourly cap hit` — notification caps working correctly
- `stf_formation_requested` with small candidate pools — expected for new orgs
- `dormain_tag_suggested` — Inferential Engine proposing a Dormain classification;
  a Circle member will accept or correct it

---

## Interpreting anomaly flags

The Integrity Engine flags anomalies to the ledger. Query them:

```bash
GET /ledger?event_type=anomaly_flagged&page=1&page_size=100
```

Or via the Ledger page in the frontend → filter by type.

### Anomaly types

**`COMPETENCE_SPIKE`**
A member gained >50 ΔC in a single activity. The change is held as `pending_audit`.

Resolution: the Org Integrity Circle reviews the evidence. If the endorsements are
sound (strong justification, high-competence reviewers, evidence links), approve by
clearing the `pending_audit` flag via a `sys_bound` motion or a vSTF verdict.

**`AUDITOR_AUDITEE_CORRELATION`**
Statistical pattern: a reviewer is consistently scoring the same target member
unusually highly or lowly across multiple STF instances.

Resolution: flag for Judicial Circle consideration. A jSTF investigation determines
whether this is genuine domain preference, bias, or coordinated manipulation.
The Integrity Engine will have already noted the pattern in the M_cmp calculation.

**`SYBIL_PATTERN` / `COORDINATED_ENDORSEMENT`**
Multiple members showing correlated activity timing, voting patterns, or
mutual endorsement networks inconsistent with organic participation.

Resolution: Judicial Circle commissions a jSTF. The M_cmp multiplier for suspected
members is frozen pending investigation. If confirmed, sanctions are applied via
the Meta-aSTF ruling.

**`VOTE_WEIGHT_CONCENTRATION`**
A single member's competence-weighted vote share exceeded the configured threshold
in a specific Cell.

Resolution: This is advisory, not blocking. The Inferential Engine surfaces a
participation-breadth suggestion to the Cell. The vote itself is not invalidated.
If concentration is persistent, the Governance Circle may consider adjusting
pass_threshold or adding members to the relevant Circle.

**`GATE2_DIFF_FAILURE`**
A sys_bound resolution was contested — applied parameter values differed from the
specification.

Resolution: This is a system integrity issue. Check `GET /motions/:id` for the
`gate2_diffs` field to see which parameters mismatched. Likely cause: concurrent
writes or an Integrity Engine crash mid-transaction. File a new motion to re-enact.

---

## Chain integrity

The ledger hash chain should always verify clean. If `GET /ledger/verify` returns
`status: "broken"`:

1. Note the `first_broken_event_id`
2. Check recent Integrity Engine logs for errors around the broken event's timestamp
3. Check for any direct database modifications (which should never happen)
4. The broken event and all subsequent events are suspect — do not trust governance
   decisions recorded after the break

**Prevention:** Never allow direct database access except via `orbsys_migrations` for
schema changes. All governance writes must go through the Integrity Engine.

---

## Running agent simulation scenarios

The agent simulation engine (`tests/agents/`) is a standalone test harness.
It requires the API to be running.

```bash
cd tests/agents
pip install -e .

# Provision the test org (run once)
python setup.py

# Run scenarios
python runner.py --scenario normal    --agents 50  --duration 300
python runner.py --scenario sybil     --agents 200 --duration 600 --report sybil.json
python runner.py --scenario capture   --agents 100 --duration 600
python runner.py --scenario collusion --agents 80  --duration 400
python runner.py --scenario stress    --agents 500 --concurrent 100 --duration 300
python runner.py --scenario mixed     --agents 200 --spawn-rate 15 --duration 600
python runner.py --scenario all       --agents 80  --duration 240 --report all.json
```

### Reading scenario output

After a scenario run, the summary shows:

```
==============================================================
  Scenario: SYBIL
  Duration: 612.3s
==============================================================
  Population:    200 agents (40 genuine, 160 adversarial)
  Active agents: 73% participated

  Governance lifecycle:
    Commons threads:    47
    Deliberation cells: 12
    Motions filed:      8
    Resolutions:        3
    STF panels:         11
    Gate 1 rejection:   27.3%

  Agent actions: 312 posts | 89 contributions | 201 votes | 44 reviews | 19 verdicts

  PAAS validation:
    Ledger chain: ✓ intact
    Anomaly flags: 7

  Security detections:
    Sybil:     DETECTED
    Capture:   clean
    Collusion: clean
==============================================================
```

**What to look for:**

- **Gate 1 rejection rate:** In the `normal` scenario, expect 5–15%. Higher rates
  indicate thin deliberation quality. Sybil scenarios may push this higher as aSTFs
  catch coordinated motions.
- **Anomaly flags > 0:** Expected in adversarial scenarios. In `normal`, any flags
  warrant investigation.
- **Sybil/Capture/Collusion detected:** These should trigger in adversarial scenarios
  and be absent in `normal`. If DETECTED appears in `normal`, the threshold for
  the relevant anomaly type may be too sensitive.
- **Ledger chain intact:** Must always be `✓`. Any failure here is a critical bug.

### Using the JSON report

```bash
python runner.py --scenario all --agents 100 --duration 300 --report results.json
cat results.json | python -m json.tool
```

The report includes per-scenario metrics and a top-level `summary` block:

```json
{
  "summary": {
    "any_ledger_broken": false,
    "any_anomaly_detected": true,
    "sybil_detected_in": ["sybil"],
    "capture_detected_in": [],
    "collusion_detected_in": ["collusion"]
  }
}
```

---

## Governing the governance system

The governance system governs itself. Parameters are changed via `sys_bound` motions.

### Common governance motions

**Adjust novice slot floor:**
```
Motion type:  sys_bound
Parameter:    novice_slot_floor_pct
New value:    0.35
Justification: Cycle 3 data shows novice completion rate of 91% — increasing floor
               to strengthen inclusion. Evidence: aSTF report aSTF-009 attached.
```

**Change membership policy:**
```
Motion type:  sys_bound
Parameter:    membership_policy
New value:    "invite_only"
Justification: Growth phase complete. Shifting to curated membership to maintain
               competence density. New members invited by existing Circle members.
```

**Create a new Circle:**
```
Motion type:  non_system
Directive:    The Governance Circle commissions an xSTF to draft the mandate,
              Dormain assignments, and initial membership criteria for a new
              Security Audit Circle. The xSTF reports within 3 weeks.
              The Governance Circle will file a follow-up sys_bound motion to
              instantiate the Circle via POST /org/circles.
Implementing circles: [Governance Circle ID]
```

**Respond to a jSTF ruling:**
```
Motion type:  non_system
Directive:    The Membership Circle implements the Meta-aSTF ruling [ref: jSTF-003]:
              member @handle is suspended for 60 days effective immediately.
              Reinstatement requires a vSTF review of their subsequent contributions.
Implementing circles: [Membership Circle ID]
```

### Org parameter reference

| Parameter | Type | Default | Description |
|---|---|---|---|
| `membership_policy` | enum | `open_application` | `open_application`, `invite_only`, `closed` |
| `novice_slot_floor_pct` | float 0–1 | `0.30` | Minimum fraction of STF slots for W_s < 800 |
| `pass_threshold_pct` | float 0–1 | `0.50` | Weighted vote fraction required to pass |
| `quorum_pct` | float 0–1 | `0.50` | Minimum participation fraction for valid vote |
| `stf_min_size` | int 3–21 | `3` | Minimum STF panel size |
| `stf_max_size` | int 3–21 | `9` | Maximum STF panel size |
| `stf_rotation_weeks_min` | int | `2` | Minimum STF mandate length |
| `stf_rotation_weeks_max` | int | `12` | Maximum STF mandate length |
| `commons_visibility` | enum | `members_only` | `members_only`, `public`, `circle_only` |
| `c_max` | float | `120.0` | Maximum ΔC per single activity |
| `t_audit` | float | `50.0` | ΔC threshold that triggers pending_audit |
| `decay_half_life_months` | float | `12.0` | W_s decay half-life (default, per-Dormain overridable) |
| `decay_floor_pct` | float 0–1 | `0.30` | W_s floor as fraction of peak |
| `volatility_k_new` | int | `60` | K-factor for new users |
| `volatility_k_established` | int | `30` | K-factor for established users |
| `volatility_k_veteran` | int | `10` | K-factor for veteran users |

---

## Backup and recovery

### Database backup

```bash
# Full backup
docker compose exec postgres pg_dump \
  -U orbsys_migrations orbsys > backup_$(date +%Y%m%d).sql

# Ledger events only (for audit purposes)
docker compose exec postgres psql -U orbsys_app orbsys \
  -c "COPY ledger_events TO STDOUT" > ledger_$(date +%Y%m%d).csv
```

### Verifying backup integrity

After restoring from backup, verify the hash chain immediately:

```bash
docker compose exec api python -c "
import asyncio
from src.services.ledger import LedgerService
from src.core.database import get_db
# run verify_chain for each org
"
```

Or via the API: `GET /ledger/verify` for each org.

### NATS JetStream

NATS stream state is not the source of truth — the PostgreSQL ledger is.
If NATS loses state, the engines will re-establish their consumers.
Historical events are in the DB; only future events flow through NATS.
