# Orb Sys — Technical Reference

> Implementation guide for contributors and integrators. Version 1.0 — fully runnable.

---

## Table of Contents

1. [Governance model in one page](#1-governance-model)
2. [Service topology](#2-service-topology)
3. [Database architecture](#3-database-architecture)
4. [Authentication and token model](#4-authentication-and-token-model)
5. [The competence layer](#5-the-competence-layer)
6. [The governance lifecycle](#6-the-governance-lifecycle)
7. [STF and blind review isolation](#7-stf-and-blind-review-isolation)
8. [The engine trinity](#8-the-engine-trinity)
9. [The ledger](#9-the-ledger)
10. [Bootstrap sequence](#10-bootstrap-sequence)
11. [Member join flow post-bootstrap](#11-member-join-flow-post-bootstrap)
12. [API conventions](#12-api-conventions)
13. [Implementation status v1.0](#13-implementation-status)
14. [Design decisions and rationale](#14-design-decisions-and-rationale)

---

## 1. Governance model

PAAS replaces positional authority with demonstrated expertise.

**Dormain** — a knowledge domain. All competence is domain-specific. A veteran cryptographer carries no special weight in a community onboarding discussion.

**W_s (Soft Competence)** — earned through peer-reviewed contribution. Grows via ΔC formula. Decays if inactive. This is the primary vote weight.

**W_h (Hard Competence)** — verified external credentials (degree, certification, patent, license). Boosts W_s on verification. Gates jSTF eligibility and W_h-minimum Circles.

**Circle** — closed, competence-gated body with mandate over specific Dormains. Decides and implements. The locus of autonomy in PAAS.

**STF (Short-Term Facilitator)** — temporary task body. Types: xSTF (deliberation quorum), aSTF (Gate 1/2 audit), vSTF (W_h verification), jSTF (judicial track).

**Commons** — open discussion space. Sponsorship converts a thread into a Deliberation Cell.

**Cell** — deliberation workspace. Invited Circles deliberate, vote competence-weighted, crystallise a motion.

**Motion types:** `sys_bound` (parameter change, Integrity Engine executes atomically), `non_system` (directive to Circles, `implementing_circle_ids` required), `hybrid` (both).

**Resolution** — enacted motion. Immutable ledger record.

**Lifecycle:**
```
Commons thread
  → sponsor (Circle member with Dormain mandate)
    → Deliberation Cell
      → Circles deliberate async + Insight Engine rolling minutes
        → Crystallise → motion draft (on-demand)
          → Competence-weighted vote
            → Gate 1: blind parallel aSTF review
              → approve   → Resolution → implementation → Gate 2
                             → enacted_locked
                             → Contested (diff fail / non-compliance)
              → revision  → Cell reactivates with directive
              → reject    → archived + public report
```

---

## 2. Service topology

| Service | Port | DB Role | Access |
|---|---|---|---|
| `apps/api` | 8000 | `orbsys_app` | SELECT + INSERT on application tables |
| `apps/blind` | 8001 | `orbsys_blind` | Narrow SELECT on STF content, INSERT on verdicts only |
| `services/integrity` | — | `orbsys_integrity` | Full SELECT + INSERT, exclusive ledger writer |
| `services/inferential` | — | `orbsys_inferential` | SELECT only |
| `services/insight` | — | `orbsys_insight` | SELECT only (RLS excludes blind cells) |

All governance actions emit to NATS JetStream stream `ORG.<org_id>.events`. All three engines subscribe as durable consumers.

**One synchronous path:** `resolution_enact_requested` — API awaits Integrity Engine NATS reply (30s timeout). All other events are fire-and-forget.

**Blind Review API** accepts only `X-Isolated-View-Token`. Session tokens → 403, not 401.

---

## 3. Database architecture

**Migrations:**

| File | Contents |
|---|---|
| `0001_initial_schema.py` | 32 tables, append-only triggers, hash chain, all role grants |
| `0002_notifications_feed_scores.py` | `notifications`, `feed_scores` |
| `0003_member_applications.py` | `member_applications` — post-bootstrap join queue |

Run: `alembic upgrade head`

**Append-only tables** (UPDATE/DELETE → exception): `ledger_events`, `delta_c_events`, `delta_c_reviewers`, `cell_contributions`, `cell_votes`, `stf_verdicts`, `stf_unsealing_events`, `commons_posts`.

**Identity sealing:** `stf_verdicts` has **no `reviewer_id` column** — structural absence, not permission. Identity lives only in `stf_assignments.member_id`, joinable only via `orbsys_integrity` role.

**Hash chain:** `event_hash = SHA-256(event_id || payload_json || prev_hash)`. Verifiable via `GET /ledger/verify`.

**Org isolation:** Row-Level Security per `org_id` at DB layer.

---

## 4. Authentication and token model

Two structurally incompatible token types. Wrong type → **403**, not 401.

**Session token** (`type: "access"`): `sub`, `org`, `state`, `exp`. State embedded at issue — changes take effect on next refresh.

**Isolated view token** (`type: "isolated_view"`): `stf_instance_id`, `assignment_id`, `exp`. No `member_id`, no `org_id`. Accepted **only** by `apps/blind`.

**Access tiers:** T0 (public), T1 (authenticated), T2 (active), T3 (governance writer), T4 (blind STF — isolated token), T5 (Integrity Engine only).

```python
ActiveMember   # T2 — FastAPI dependency alias
GovWriter      # T3
BlindCtx       # T4
```

---

## 5. The competence layer

**ΔC formula:**
```
ΔC_u,d = G · K · Σ_r [(S_r − 0.5) · w_r,d · M_r,d] / Σ_r [w_r,d · M_r,d]
```

| Symbol | Values |
|---|---|
| G (gravity) | 0.5 Commons, 1.0 Cell/motion, 1.2 audit |
| K (volatility) | 60 new → 30 established → 10 veteran (by proof_count) |
| S_r (reviewer score) | 0.0–1.0, centred at 0.5 (neutral = no effect) |
| M_r,d (circle multiplier) | 1.6 primary, 1.2 secondary, 1.0 unrelated |

- Formal reviewers only — casual reactions generate no ΔC
- C_max = 120 (cap per activity)
- T_audit = 50 (triggers pending_audit hold)
- Decay: Dormain-governed, default exponential 12-month half-life, 0.3 × peak floor
- **Integrity Engine is the only ΔC writer**

**W_h:** On vSTF verification: `W_s = max(W_s, W_h)`. Does not directly vote.

**Curiosity (B_u):** Self-declared. Zero vote weight. Used by Inferential Engine for feed relevance and STF candidate scoring.

---

## 6. The governance lifecycle

**sys_bound:** Dry-run at `POST /motions/:id/validate-specification`. Gate 2 = automated diff — any mismatch → Contested, no partial writes.

**non_system:** `implementing_circle_ids` required (422 if absent, enforced at Pydantic + service). Gate 2 = interpretive aSTF per implementing Circle.

**hybrid:** Both blocks validated and audited independently.

**Gate 1 aSTF:** Commissioned by Inferential Engine. 30% novice floor. Dormain gap-filling composition bias. Independence from filing Circle enforced. Verdicts: `approve`, `reject`, `revision_request`.

---

## 7. STF and blind review isolation

Three-layer stack:

1. **Token middleware** — Blind API rejects session tokens (403)
2. **Schema** — `stf_verdicts` has no `reviewer_id` column
3. **DB role** — join to `stf_assignments.member_id` only via `orbsys_integrity`

Unsealing: two conditions only — malpractice finding, or jSTF penalty on named individual. Both recorded in `stf_unsealing_events`.

| STF type | Sealed | Composition |
|---|---|---|
| xSTF | No | Competence + curiosity matched |
| aSTF | Yes | Independence-biased, gap-filling |
| vSTF | Yes | Same-Dormain competence required |
| jSTF | Yes | W_h ≥ 2400 in relevant domain |

---

## 8. The engine trinity

### Inferential Engine

Handles: `stf_commissioned`, `commons_thread_created/post_created`, `cell_created`, `dormain_tag_applied`, `wh_claim_submitted`, `motion_gate1_result` (approve), `member_application_submitted`.

- **STF matching:** `score = competence_fit × curiosity_fit × availability × independence`
- **`wh_claim_submitted`:** Creates vSTF instance, scores same-Dormain candidates, forms assignments
- **`motion_gate1_result` (approve):** Fan-outs P2 notification to implementing circle members
- **`member_application_submitted`:** Fan-outs P2 notification to Membership Circle members
- **Homogeneity flag:** >80% Dormain overlap among invited Circles → advisory to sponsor

### Insight Engine

Handles: `sponsor_draft_requested`, `cell_crystallise_requested`, `cell_contribution_added`, `stf_assignment_created`, `motion_filed`, `motion_revision_requested`, `stf_deadline_approaching`.

- **Draft generation is on-demand only** (trigger = click, not background)
- **Rolling minutes:** structured JSON updated on each contribution
- **Notification caps:** P1 always; P2 max 12/day, 3/hour; P3 digest-only (v1.0: deferred)
- **Deadline monitor:** background task every 30 minutes

### Integrity Engine

Handles (with side-effects): `formal_review_filed` (ΔC), `wh_claim_verified` (W_h boost), `resolution_enact_requested` (atomic writes), `stf_verdict_filed` (aggregate + Gate 1 trigger), `motion_gate1_result` (motion state + Resolution creation), `stf_formation_requested` (assignments + isolated_view tokens), `notification_write_requested` (fan-out: resolves `member_list` / `implementing_circles` targets), `feed_scores_write_requested`.

All other events: written to ledger only (LEDGER_ONLY set).

**Atomic enactment:** Apply all parameters → Gate 2 diff → if all match: `enacted_locked`. If any fail: rollback all, `Contested`. No partial enactment.

---

## 9. The ledger

Immutable append-only. `SHA-256(event_id || payload_json || prev_hash)`.

Corrections: new row with `supersedes = <original_event_id>`.

`GET /ledger/verify` — recomputes full chain. Returns `{ status, verified_events, first_broken_event_id }`.

---

## 10. Bootstrap sequence

```
1. POST /org                     org created, bootstrapped_at = null
2. POST /org/dormains            define Dormains
3. POST /auth/register           founding members (bootstrap-only path)
4. POST /org/circles             circles + dormain mandates
                                 (invites auto-confirm during bootstrap)
5. POST /competence/wh-claims    optional — vSTF verifies credentials
6. POST /org/bootstrap-complete  { membership_policy }
                                 bootstrapped_at = now()
                                 founding circles dissolved
                                 default org parameters seeded
                                 POST /auth/register → 403 hereafter
```

The seed script (`python -m src.scripts.seed`) performs all six steps automatically.

---

## 11. Member join flow (post-bootstrap)

```
POST /members/apply?org_slug=<slug>
  { handle, display_name, email, password, motivation?, expertise_summary? }
  → MemberApplication created (pending)
  → Membership Circle members notified (P2)

GET  /members/applications?status=pending    GovWriter access
POST /members/applications/:id/review
  { approve: true, note? }
  → Member account created → applicant can login
```

**Policy** (`membership_policy` org parameter): `open_application`, `invite_only`, `closed`. Changing policy requires a `sys_bound` governance motion.

---

## 12. API conventions

**69 routes** across 10 domains. Full OpenAPI spec at `GET /docs`.

Paginated response: `{ items, total, page, page_size, has_next }`

Key error strings: `AUTH_STATE_SUSPENDED`, `STF_BLIND_TOKEN_REQUIRED`, `MOTION_MISSING_CIRCLES`, `CHAIN_INTEGRITY_FAILURE`, `ALREADY_BOOTSTRAPPED`, `BOOTSTRAP_ONLY`, `INVITE_REQUIRES_MEMBERSHIP`, `MEMBERSHIP_CLOSED`, `MEMBERSHIP_INVITE_ONLY`, `ENGINE_NOT_RUNNING`, `ENGINE_TIMEOUT`.

Full route list — see README.md §Stack for the summary table or `GET /docs` for the OpenAPI spec.

---

## 13. Implementation status

### v1.0 — complete

- **API:** 69 routes, all 10 service domains implemented
- **list_cells:** access-controlled (open, invited-circle, initiator)
- **Member join flow:** apply → review → create — full lifecycle
- **bootstrap_complete:** org lifecycle, parameter seeding
- **validate_specification:** dry-run (fix: `OrgParameter.parameter` column)
- **invite_member:** immediate acceptance in v1.0
- **DB:** 3 migrations, 34 tables, append-only, hash chain, 5 roles
- **Engines:** all event handlers wired including vSTF commission, fan-out notifications
- **Frontend:** 18 pages, invite form, application queue, notification badge
- **Test agents:** 6 scenarios, LLM-powered, auto-approver for join flow

### v1.1 — deferred

- Circle invitation via Circle vote
- Endorsement provenance weighting in ΔC
- Cross-Dormain transfer coefficients
- Server-side token revocation
- P3 digest notifications
- Voluntary STF identity disclosure
- Blockchain ledger backend

---

## 14. Design decisions and rationale

**Blind review is structural, not a permission flag.** `stf_verdicts` has no `reviewer_id` column. There is nothing to expose — structural absence is stronger than permission-based absence.

**Non-system resolutions require executing Circles.** A directive that names no responsible body is a wish. `implementing_circle_ids` enforces accountability before filing.

**Founding Circle dissolves completely.** Legitimacy flows from ongoing contribution. No founding emeritus role.

**W_s decays, W_h does not.** W_s reflects active contribution and should decay with inactivity. W_h reflects external credentials with their own expiry mechanism, governed by the credentialing body.

**bootstrapped_at = null is not suspended governance.** Everything during bootstrap is in the ledger under the same rules as live operations.

**invite_member is immediate in v1.0.** The inviting member must already be in the Circle — their judgment is the v1.0 gate. The Circle-vote mechanism does not change the data model; it adds a `circle_invitations` table and a vote step in v1.1.

**ΔC only counts formal reviewers.** Casual reactions are cheap signals easily gamed. Formal reviews commit a score under the reviewer's own W_s — divergence from later audits reduces their endorser weight. The endorsement process is itself meritocratic.
