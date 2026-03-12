# Orb Sys — Technical Reference

> Implementation guide for contributors and integrators.
> Covers the governance model as it translates to code, architectural decisions,
> data layer constraints, API contract, engine behaviour, and known sharp edges.

---

## Table of Contents

1. [Governance model in one page](#1-governance-model-in-one-page)
2. [Service topology](#2-service-topology)
3. [Database architecture](#3-database-architecture)
4. [Authentication and token model](#4-authentication-and-token-model)
5. [The competence layer](#5-the-competence-layer)
6. [The governance lifecycle](#6-the-governance-lifecycle)
7. [STF and blind review isolation](#7-stf-and-blind-review-isolation)
8. [The engine trinity](#8-the-engine-trinity)
9. [The ledger](#9-the-ledger)
10. [Bootstrap sequence](#10-bootstrap-sequence)
11. [API conventions](#11-api-conventions)
12. [Implementation status](#12-implementation-status)
13. [Design decisions and rationale](#13-design-decisions-and-rationale)

---

## 1. Governance model in one page

PAAS (Polycentric Autonomy-Audit System) replaces positional authority
with demonstrated expertise. The key primitives:

**Dormain** — a knowledge domain. All competence is domain-specific.
There is no global seniority. A veteran cryptographer has no special
weight in a governance discussion about community onboarding.

**W_s (Soft Competence)** — earned through peer-reviewed contribution.
Grows via the ΔC formula. Decays over time if a member becomes inactive.
This is the primary vote weight for all governance decisions.

**W_h (Hard Competence)** — verified external credentials. Degree, certification,
patent, license, or verified contribution. Verified by vSTF peer review.
Gates jSTF eligibility and W_h-minimum Circles. Does not directly set vote weight,
but boosts W_s to at least W_h on verification.

**Circle** — a group of members with mandate over specific Dormains.
The deliberating and deciding body. Circles vote on motions. Votes are
weighted by W_s in the relevant Dormain.

**STF (Short-Term Facilitator)** — a temporary body commissioned for a
specific mandate. The audit layer. Four types:
- **xSTF** — deliberative quorum for Cell work
- **aSTF** — independent audit of motions (Gate 1) and enacted resolutions (Gate 2)
- **vSTF** — blind peer verification of W_h credential claims
- **jSTF** — judicial track for systemic integrity failures

**Commons** — the org-wide discussion space. Ideas form here.
Sponsorship converts a thread into a Deliberation Cell.

**Cell** — the deliberation workspace. Invited Circles deliberate,
produce a motion, vote, crystallise.

**Motion** — a formal proposal. Three types:
- **sys_bound** — changes governed parameters. Executed by the Integrity Engine.
  Gate 2 is an automated diff. No executing Circle needed.
- **non_system** — a directive to one or more Circles. Gate 2 is an interpretive
  audit. **Requires `implementing_circle_ids` — non-null.** 422 if absent.
- **hybrid** — both. Requires executing Circles for the directive part.

**Resolution** — an enacted motion. Immutable ledger record.

**The governance lifecycle:**
```
Commons thread
  → sponsor (Circle member)
    → Deliberation Cell opens
      → xSTF deliberates
        → motion crystallised (Insight Engine draft, on-demand)
          → voted (competence-weighted)
            → Gate 1 (aSTF reviews)
              → [approve] → Resolution created → implementation
                → Gate 2 (diff or interpretive audit)
                  → [match] → enacted
                  → [fail] → Contested
              → [revision_request] → Cell reactivates with directive
              → [reject] → Cell dissolved, public report
```

---

## 2. Service topology

### Services and their DB roles

| Service | Port | DB Role | Access |
|---|---|---|---|
| `apps/api` | 8000 | `orbsys_app` | SELECT + INSERT on most tables |
| `apps/blind` | 8001 | `orbsys_blind` | Narrow SELECT on STF content, INSERT on verdicts |
| `services/integrity` | — | `orbsys_integrity` | Full SELECT + INSERT, exclusive writer |
| `services/inferential` | — | `orbsys_inferential` | SELECT only |
| `services/insight` | — | `orbsys_insight` | SELECT only (excludes blind cells) |

DB role boundaries are enforced at the PostgreSQL connection level.
A service connecting with the wrong role will receive a permissions error,
not silently wrong data.

### Event flow

All governance actions emit events to NATS JetStream. Stream name:
`ORG.<org_id>.events`. All three engines consume all events (`durable`
consumers). Events carry `ledger_event_id` — initially null, populated
after the Integrity Engine commits. Other engines wait on the populated version
before acting on an event.

**One exception: `resolution_enact_requested` (sys-bound only).** This
is a synchronous path — the API waits on the Integrity Engine atomic write
before returning to the caller. Diff failure returns `Contested` with no
partial writes. All other governance events are async.

### Blind Review API isolation

The Blind Review API (`apps/blind`) sits on an isolated network.
It is not reachable from the main API, only from the client directly.
It accepts only `X-Isolated-View-Token` headers — session Bearer tokens
return 403, not 401. This is intentional: wrong token type is not an
authentication failure, it is an access control failure.

---

## 3. Database architecture

### Role model

```sql
orbsys_app         — SELECT, INSERT on application tables
orbsys_blind       — SELECT on stf content, INSERT on stf_verdicts only
orbsys_integrity   — SELECT, INSERT on all tables (exclusive writes on ledger)
orbsys_inferential — SELECT only
orbsys_insight     — SELECT only (RLS blocks blind cell content)
orbsys_migrations  — schema owner, used by Alembic only
```

Default privileges are set in `infra/postgres/init.sql` and inherited by
all future tables. Specific column-level grants (e.g. blocking `orbsys_app`
from reading `stf_assignments.member_id` on blind STF types) are applied
in migrations.

### Append-only tables

The following tables are append-only, enforced by triggers at the DB layer:

```
ledger_events          — governance history, never updated
delta_c_events         — competence computation history
delta_c_reviewers      — reviewer scores (internal to Integrity Engine)
cell_contributions     — Cell record
cell_votes             — vote record
stf_verdicts           — STF verdicts
stf_unsealing_events   — identity unsealing record
commons_posts          — post history
```

Trigger function `enforce_append_only()` is defined in `init.sql` and
applied to each table in migrations. UPDATE and DELETE raise an exception.
Corrections create new rows with `supersedes = <old_row_id>`.

### Hash chain

Every `ledger_events` row carries `prev_hash` and `event_hash`.

```
event_hash = SHA-256(event_id || payload_json || prev_hash)
```

The chain is verifiable by any active member via `GET /ledger/verify`.
Breaking the chain (editing any row) is detectable. This is the
tamper-evidence guarantee.

### Org isolation

Every table carries `org_id`. Row-Level Security is applied at the DB
layer — a connection for org A cannot read org B's data even if the
application has a bug. `SET LOCAL app.current_org_id = '<uuid>'` is
set by the connection pool per request.

### Identity sealing design

`stf_verdicts` has **no `reviewer_id` column.** This is a design choice,
not a permission omission. Identity lives only in `stf_assignments.member_id`.
The join between `stf_verdicts` and `stf_assignments` is available only via
the `orbsys_integrity` role. No code path in the application API can
expose reviewer identity for blind STF types.

Unsealing is recorded in `stf_unsealing_events` and occurs only on:
1. Malpractice finding by a later aSTF
2. jSTF penalty on a named individual

After an unsealing event is created, `stf_assignments.member_id` becomes
queryable for that specific `assignment_id`.

---

## 4. Authentication and token model

### Token types

Two token types are structurally incompatible. The `type` claim
distinguishes them. Wrong type on any endpoint returns **403**, not 401.

**Session token** (`type: "access"`)
```json
{
  "sub": "<member_id>",
  "org": "<org_id>",
  "state": "<member_state>",
  "type": "access",
  "exp": "<timestamp>"
}
```
Member state is embedded in the token. State changes (suspension, review)
take effect on the next token refresh, not immediately. This is a
deliberate trade-off — immediate revocation requires server-side state
(v1.1).

**Isolated view token** (`type: "isolated_view"`)
```json
{
  "stf_instance_id": "<uuid>",
  "assignment_id": "<uuid>",
  "type": "isolated_view",
  "exp": "<timestamp>"
}
```
No `member_id`. No `org_id`. Scoped to a single STF assignment.
Expires at deadline or 14 days, whichever is sooner.
Accepted **only** by `apps/blind`.

### Access tiers

| Tier | Description | Dependency |
|---|---|---|
| T0 | Public read | None |
| T1 | Authenticated member | Valid session token |
| T2 | Active member | T1 + state not in blocked set |
| T3 | Governance writer | T2 + state allows governance writes |
| T4 | STF assigned (blind) | Valid isolated view token |
| T5 | Integrity Engine | Engine token (never issued to members) |

Blocked states for governance writes: `suspended`, `under_review`,
`inactive`, `exited`.

Fully blocked states (no read access): `suspended`, `exited`.

### FastAPI dependencies

```python
# Type aliases — use in route signatures
ActiveMember   # T2 — active member
GovWriter      # T3 — governance write permitted
BlindCtx       # T4 — isolated view token only
DB             # SQLAlchemy async session
```

Example:
```python
@router.post("/commons/threads/{thread_id}/sponsor")
async def sponsor(thread_id: UUID, member: GovWriter, db: DB):
    ...
```

---

## 5. The competence layer

### W_s (Soft Competence) — the ΔC formula

```
ΔC_u,d = G · K_u,d · Σ[(S_r − 0.5) · w_r,d · M_r,d]
          ────────────────────────────────────────────
                      Σ[w_r,d · M_r,d]
```

| Symbol | Meaning | Values |
|---|---|---|
| G | Activity gravity | 0.5 Commons, 1.0 Cell/motion, 1.2 audit |
| K | User volatility | 60 new, 30 established, 10 veteran |
| S_r | Reviewer score | 0.000–1.000 (centred at 0.5) |
| w_r,d | Reviewer's W_s in Dormain d | Current value at review time |
| M_r,d | Circle membership multiplier | 1.6 primary, 1.2 secondary, 1.0 unrelated |

**Important constraints:**
- R = formal reviewers only. Casual reactions generate no ΔC.
- K decreases as `proof_count` increases (new → established → veteran).
  This is automatic; there is no admin action to change it.
- Max single-event gain: C_max = 120 pts. Gain above this is capped.
- Audit trigger: T_audit = 50 pts in a single event. Held as
  `pending_audit`, Org Integrity Circle notified.
- Decay is Dormain-governed. Default: exponential, 12-month half-life,
  0.3 × W_s_peak floor. Decay parameters are sys-bound governed —
  changeable only via enacted Resolution.

**The Integrity Engine is the only writer of ΔC.** The app API emits a
`formal_review_filed` event. The Integrity Engine consumes it, loads the
reviewer pool from `delta_c_reviewers`, computes ΔC, writes to
`delta_c_events`, and updates the materialised `competence_scores` row.

### W_h (Hard Competence)

Verified external credentials. On verification:
- W_h value is written to `wh_credentials`
- W_s is boosted: `w_s = max(current_w_s, w_h)` for the relevant Dormain
- Both events are written to the ledger atomically

**W_h does not directly weight votes.** It sets a floor on W_s and gates
access to jSTF and W_h-minimum Circles.

### Curiosity (B_u)

Self-declared interest vectors. Written to `curiosities`.
Zero governance weight. Used exclusively by the Inferential Engine for:
- Feed relevance scoring: `max(mandate_match, curiosity_match)`
- STF candidate matching: curiosity_fit term in candidate_score
- Novice slot prioritisation within the novice pool

Curiosity is free to update at any time. No review, no audit.

---

## 6. The governance lifecycle

### Motion types and their contracts

**sys_bound**
- Parameters are defined, range-validated, justification-required
- Pre-validation dry-run available: `POST /motions/:id/validate-specification`
  (no state change, no event)
- Gate 2: automated diff by Integrity Engine. If all `specified_value`
  fields match `applied_value` fields → enacted. Any mismatch → Contested.
  Contested means no partial write occurred. The system is consistent.
- No `implementing_circle_ids` required or expected.

**non_system**
- Carries a `MotionDirective` with body, commitments, flagged ambiguities
- **`implementing_circle_ids` is required at filing time.** The `file-motion`
  endpoint returns 422 if absent for non_system or hybrid motions.
  This is enforced at the service layer, not the DB layer (field is nullable
  in the schema to allow sys_bound motions).
- Gate 2: interpretive audit by aSTF. Each implementing Circle is assessed
  independently. "Did Circle X implement the directive faithfully?"
- Multi-circle execution: accountability is per-Circle. One Circle's
  non-implementation does not affect another Circle's Gate 2 result.

**hybrid**
- Carries both a directive and specifications
- Both parts are drafted independently by the Insight Engine
- Both parts are validated independently at Gate 1
- Gate 2: Integrity Engine diff for the sys-bound part +
  interpretive aSTF for the directive part
- Requires `implementing_circle_ids` for the directive part.

### Gate 1 — aSTF review

The aSTF is commissioned by the Inferential Engine after a motion is filed.
Composition is biased toward:
- Members not in the filing Circle (independence)
- Members who fill Dormain gaps identified in the Cell composition profile
- Novice slots: 30% floor applies to aSTF as to any xSTF

The aSTF has three possible verdicts:
- `approve` → Resolution created, moves to implementation
- `reject` → Motion archived, public report filed to ledger
- `revision_request` → Cell reactivated with specific directive attached.
  Ignored Revision Requests are visible to the next Gate 1 panel.

### Gate 2 — post-implementation audit

| Motion type | Gate 2 agent | What is checked |
|---|---|---|
| sys_bound | `astf_diff` (automated) | Parameter values match specification exactly |
| non_system | `astf_interpretive` | Implementing Circle(s) executed directive faithfully |
| hybrid | Both | Both checks independently |
| W_h credential | `vstf` | Credential claim is accurate |
| Judicial finding | `jstf` | Due process, evidence quality |

---

## 7. STF and blind review isolation

### STF types

| Type | Purpose | Identity sealed? | Composition |
|---|---|---|---|
| xSTF | Cell deliberation quorum | No | Competence + curiosity matched |
| aSTF (motion) | Gate 1 audit | Yes | Independence biased, gap-filling |
| aSTF (periodic) | Circle health | Yes | Independence biased |
| vSTF | W_h credential verification | Yes | Same-Dormain competence |
| jSTF | Judicial track | Yes | W_h minimum required |
| meta-aSTF | aSTF audit | Yes | External pool |

### The isolation stack (3 layers)

**Layer 1 — Token type enforcement (middleware)**
The Blind Review API rejects session Bearer tokens at the middleware level.
`X-Isolated-View-Token` is required. Wrong type → 403.

**Layer 2 — Query scope (data layer)**
No application code path joins `stf_verdicts → stf_assignments`.
`stf_verdicts` has no `reviewer_id` column. The only way to connect a
verdict to an identity is via `stf_assignments.member_id`, which is
accessible only to the `orbsys_integrity` role.

**Layer 3 — Aggregation gate (Integrity Engine only)**
When the Integrity Engine computes the aggregate verdict for a completed
STF, it is the only service with the DB role to perform the join.
The aggregated result (verdict counts, majority outcome) is written to
the ledger and made available to the app API. Individual reviewer
identities are never exposed to the application layer.

### Unsealing

Default: permanent sealed. Two conditions trigger unsealing:
1. **Malpractice finding** — a later aSTF finds that an STF reviewer
   acted with clear bias or bad faith in a specific past instance
2. **Judicial penalty** — a jSTF names a specific individual in a penalty ruling

On unsealing: `stf_unsealing_events` row is created. This event, and only
this event, causes `stf_assignments.member_id` for that `assignment_id` to
become queryable outside the Integrity Engine.

Voluntary disclosure is explicitly not supported in v1.0. The PAAS authorship
strongly discourages it — reviewer independence requires that reviewers cannot
be pressured to identify themselves.

---

## 8. The engine trinity

### Inferential Engine

**Role:** router, matcher, tagger. Read-only DB access.
Never writes to DB. Emits routing events consumed by the API.

**Dormain tagging (3 layers):**
1. Author signal — member can suggest tags at post creation
2. NLP classification — engine classifies based on content
3. Human correction — any Circle member can correct; correction feeds
   retraining signal

Tuned toward recall: better to over-tag than under-tag.
Feed relevance: `max(mandate_match, curiosity_match)` — high curiosity
always surfaces content even if mandate match is low.

**STF matching:**
```
candidate_score = competence_fit × curiosity_fit × availability × independence
```

Novice floor: 30% of all xSTF slots go to members with W_s < 800 in the
relevant Dormain. Within the novice pool, curiosity_fit is the primary
sort key. This floor is a hard minimum, not a target.

Homogeneity flag: if >80% of invited Circle members share Dormain overlap,
the Inferential Engine emits a soft notification to the sponsoring member.
This is advisory — the sponsor can proceed.

**aSTF composition balancer:**
The Integrity Engine computes a Cell composition profile on demand
(`GET /cells/:id/composition-profile`). This profile identifies Dormain
gaps — areas where the Cell's deliberation has been thin. The Inferential
Engine uses this profile to bias aSTF candidate selection toward
gap-filling competences. This is a weighting factor, not a hard filter.

### Insight Engine

**Role:** scribe, drafter, scheduler. Read-only DB access.
Communicates back to the API via event bus (never direct HTTP).

**Draft generation — on-demand only:**
- Sponsor clicks → thread state is read at that moment → mandate brief drafted
- Cell crystallise → Cell state is read → motion draft produced
- No proactive generation. No drafts without a human click.

Attribution in drafts follows the narrative brief format:
```
"@jkolly, @mtracy argue X; @jtukei insists Y; @pahmed [OP] notes Z"
```
Contributors are named in context of their positions, not listed neutrally.

**Rolling Cell minutes (structured JSON):**
```json
{
  "key_positions": [...],
  "open_questions": [...],
  "emerging_consensus": [...],
  "points_of_contention": [...]
}
```
Updated on each new contribution. Stored in the Cell, readable by
all Cell participants.

**LLM isolation:**
The Insight Engine LLM sub-process has no direct DB or bus access.
Content is stripped of `org_id` before any external LLM egress.
LLM backend is configurable: `openai | anthropic | local`.

**Notification caps:**
- P1 (always): STF deadline <24h, vote closing <2h, judicial flag
- P2 (capped): invitations, sponsorships, slot offers — 12/day, 3/hour
- P3 (digest only): curiosity matches, health updates

The Insight Engine enforces these caps. P1 notifications bypass all caps.

**Does NOT:**
- Recommend votes
- Access blind-type Cell content (RLS enforced)
- Emit governance actions (read and draft only)

### Integrity Engine

**Role:** ledger and locksmith. Exclusive write access to ledger and
competence tables. Single active instance per org shard, plus standby.

**The ΔC computation:**
The Integrity Engine is the only code that reads `delta_c_reviewers`
(which contains individual reviewer scores and identities) and applies
the formula. The computed result is written to `delta_c_events`.
The materialised `competence_scores` row is updated atomically.

**Anomaly detection:**
| Type | Trigger | Response |
|---|---|---|
| TYPE 1 | ΔC spike > 50pts in a single event | `pending_audit`, notify Org Integrity Circle |
| TYPE 2 | Auditor-auditee correlation across multiple STFs | M_cmp freeze for involved members |
| TYPE 3 | Sybil-like pattern (vote weight concentration, activity timing) | Anomaly flag, jSTF consideration |
| TYPE 4 | Gate 2 diff failure | `Contested` state, no partial write |

Anomaly flags do not automatically penalise members. They trigger review
by the Org Integrity Circle and may escalate to jSTF.

**Atomic writes:**
All sys-bound resolution enactments are atomic transactions. The sequence:
1. Apply all parameter changes to `org_parameters`
2. Compute Gate 2 diff for each `motion_specifications` row
3. If all diffs match → write `resolution.state = enacted`, write ledger event
4. If any diff fails → write `resolution.state = contested`, rollback all parameter changes

There is no partial enactment. The transaction succeeds completely or
rolls back completely.

---

## 9. The ledger

### Structure

Every governance action emits a ledger event. Events are immutable rows
in `ledger_events`. Each row carries:

```
event_hash = SHA-256(event_id || payload_json || prev_hash)
```

The chain is linear per org. Breaking the chain (editing any row) produces
a hash mismatch detectable at the first changed row and every subsequent row.

### Verification

`GET /ledger/verify` walks the full chain for the current org and
recomputes all hashes. Available to all active members — this is the
public transparency guarantee.

Response:
```json
{
  "status": "ok" | "broken",
  "verified_events": 1247,
  "first_broken_event_id": null | "<uuid>"
}
```

### Corrections

Corrections create new rows with `supersedes = <original_event_id>`.
The original row is never modified. The correction is visible in the chain.
This is the audit trail — not just what happened, but what was subsequently
corrected and why.

---

## 10. Bootstrap sequence

The bootstrapping insight: **STFs can exist before Circles.** The only
prerequisite is competence weights. This means the system can bootstrap
itself using its own native mechanisms.

### The 8-step sequence

```
1. Org identity created         — org_id in DB, bootstrapped_at = null
2. Dormain templates selected   — provisional Dormains defined
3. Member registration          — members join, submit W_h proofs
   → Integrity Engine computes preliminary W_h
   → vSTF pool forms from the member pool itself
   → vSTF peer-verifies W_h claims (blind parallel, same process as live ops)
   → W_s boosted to verified W_h values
4. Founding Circle selected     — manual, subset of registered pool,
                                   reflecting prior org structure and
                                   verified competence distribution
5. Founding deliberation        — full governance lifecycle active
                                   aSTF is operational from Step 3's competence pool
                                   no bootstrap exceptions to Gate 1
6. Founding Resolution          — Founding Circle dissolves atomically on enactment
                                   bootstrapped_at = NOW()
                                   no backtracking possible
7. Competence re-evaluation     — outstanding W_h claims finalised
   + Circle population            Circles activated as quorum reached
                                   system ops live per Circle, not all at once
8. Pilot closes                 — governance judgment, not system state
                                   Org Integrity Circle declares normal ops
```

**The Founding Circle dissolves completely.** It has no mandate Dormains,
no Inferential Engine routing, no ongoing governance role. After the
founding Resolution, its members are ordinary members with ordinary
competence scores. This is the structural commitment that legitimacy
flows from ongoing contribution, not founding status.

**The `bootstrapped_at` field** is null during bootstrap and set on
founding Resolution enactment. It is the single flag that distinguishes
bootstrap from live operations. Nothing in the system is suspended during
bootstrap — the lifecycle is simply operating on a smaller initial scope.

---

## 11. API conventions

### URL structure

```
/auth/...                   — session management (no org prefix — org in token)
/members/...                — member profile and feed
/competence/...             — W_s, W_h, curiosities, leaderboard
/commons/...                — threads, posts, sponsorship, formal reviews
/cells/...                  — contributions, votes, crystallise, file-motion
/motions/...                — motion state, validation dry-run
/stf/...                    — STF instances, assignments, verdicts
/circles/...                — circle membership, health
/org/...                    — org config, parameters, dormains
/ledger/...                 — event history, chain verification, audit archive
```

Blind Review API (port 8001):
```
/blind/:stf_id/content      — Cell content for this assignment (isolated view token only)
/blind/:stf_id/verdicts     — file verdict (isolated view token only)
```

### Response envelope

Paginated responses follow a consistent structure:
```json
{
  "items": [...],
  "total": 247,
  "page": 1,
  "page_size": 25,
  "has_next": true
}
```

### Error responses

Standard FastAPI validation errors for 422. Governance-specific errors
use detail strings with a prefix:
```
AUTH_STATE_SUSPENDED     — member state blocks this action
STF_BLIND_TOKEN_REQUIRED — wrong token type on blind endpoint
MOTION_MISSING_CIRCLES   — non-system motion filed without implementing_circle_ids
CHAIN_INTEGRITY_FAILURE  — ledger hash chain broken (critical)
```

### Sync vs async

Most endpoints are async (emit event, return 202 or 201, engine processes
separately). One endpoint is synchronous by design:

**`POST /stf/:id/resolutions`** (sys-bound enactment) — waits for Integrity
Engine atomic write. Returns only when the transaction is complete.
This is the only endpoint where the caller is blocked on the engine.
Timeout: 30s. If the engine does not respond in 30s, return 503.

---

## 12. Implementation status

### Complete (scaffold)
- Directory structure and monorepo layout
- All SQLAlchemy models (org, competence, governance — every table)
- Core layer (config, database, security, dependencies)
- All router stubs with correct signatures and auth dependencies
- Alembic wired to models (migrations not yet generated)
- Engine services with NATS consumer structure and handler stubs
- ΔC formula implemented in Integrity Engine
- Frontend with design system, typed API client, Zustand store, all types
- Docker Compose for full local stack
- Postgres init with roles and append-only function

### Next: database migrations
Run `make migration MSG="initial schema"` to generate migrations from
the existing models. Review carefully — append-only triggers must be
applied to the correct tables in the migration file, not just in init.sql.

### Next: schemas layer
`apps/api/src/schemas/` is empty. Pydantic request/response models for
every router endpoint. One file per domain matching the router structure.
Start with `auth.py` and `members.py` — they unblock everything.

### Next: services layer
`apps/api/src/services/` is empty. Business logic goes here.
Routers call services. Services call models via SQLAlchemy.
Services emit events to NATS.

### Pending (v1.1)
- Endorsement provenance weighting in ΔC (`provenance_link` field exists, not computed)
- Transfer coefficients between Dormains
- Voluntary STF identity disclosure
- Server-side token revocation
- Blockchain ledger backend (EventStoreDB / Hyperledger)
- Cross-Dormain reviewer eligibility fallback for thin bootstrap pools

---

## 13. Design decisions and rationale

### Why blind review is structural, not a permission flag

A permission system says "you are not allowed to query this column."
The column still exists. A determined attacker with DB access, a compromised
role, or a code bug can expose it.

The current design says "the column does not exist." `stf_verdicts` has no
`reviewer_id`. There is nothing to expose. The join between verdicts and
identities is a dead end for anyone without `orbsys_integrity` access.

### Why non-system resolutions require executing Circles

A directive that names no responsible body is not a governance decision —
it is a wish. The `implementing_circle_ids` requirement enforces that every
non-system resolution has a named accountable party before it is filed,
not after it fails to be implemented.

Gate 2 for non-system resolutions is an interpretive audit per implementing
Circle. Each Circle's execution is assessed independently. This prevents
accountability diffusion in multi-circle resolutions.

### Why the Founding Circle dissolves completely

PAAS is explicitly designed so that legitimacy comes from ongoing
contribution, not founding status. A founding Circle that persists — even
in advisory form — creates a permanent class of members with accumulated
informal authority. The dissolution is the structural commitment to that
principle. There is no "founding emeritus" role.

### Why W_s decays and W_h does not (within credential validity)

W_s represents active, demonstrated contribution in a Dormain. A member who
was highly active in cryptography two years ago but has since moved to a
different area of work should have their cryptography influence decay.
Their community recognised their contribution at the time; the decay is not
a punishment, it is a reflection of where their current contribution lives.

W_h represents verified external credentials. A degree does not expire because
its holder has been inactive. Credentials have their own expiry mechanism
(`expires_at` on `wh_credentials`), governed by the credentialing body,
not by the org's activity metric.

### Why preliminary W_h is used to seed the bootstrap vSTF pool

The bootstrap vSTF needs reviewers with competence in the Dormain being
verified. At bootstrap, the only source of that competence is the other
founding members. Preliminary W_h values are deliberately conservative
and used exclusively for vSTF pool formation. They carry no governance
weight until verified. This is the same peer review logic the system uses
in perpetuity — it is not a special bootstrap exception.

### Why `bootstrapped_at = null` does not mean suspended governance

The temptation in bootstrapping designs is to create a "setup mode" with
special permissions or suspended process requirements. This creates
precedent for bypassing governance. The Orb Sys bootstrap has no setup mode.
Everything that happens during bootstrap is in the ledger, following the
same process rules as live operations. `bootstrapped_at = null` simply means
the founding Resolution has not yet been enacted — not that the system is
in a different mode.
