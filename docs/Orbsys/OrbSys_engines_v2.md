# Orb Sys — Engine Trinity
## Implementation Specification — v2

> v2 updates: ΔC scoped to formal reviewers only; decay domain-defined via Circle
> motion; draft proposals on-demand at sponsorship click; attribution as narrative
> brief; STF identities permanently sealed (two narrow unsealing conditions);
> transfer coefficients deferred to v1.1; aSTF composition balancer added.
>
> Cross-reference: OrbSys_v7.md §13, §17c, §19d, §20

---

## Overview

Three distinct service responsibilities, one event ledger as the shared bus.

```
Inferential Engine  — the router
  Who belongs where? What content belongs to whom?
  Input: competence vectors, curiosity vectors, dormain tags,
         Cell composition profiles (from Integrity Engine)
  Output: invitations, slot assignments, feed filters, proposal routing,
          aSTF pool composition biasing

Insight Engine      — the scribe and scheduler
  What is happening and what needs attention?
  Input: Cell content, thread content, timelines, member state
  Output: on-demand draft proposals (narrative attribution), Cell minutes,
          motion drafts, notifications, guardrail signals

Integrity Engine    — the ledger and locksmith
  What happened, is it consistent, and what is allowed to change?
  Input: all governance events, formal review outcomes
  Output: append-only log, ΔC updates (formal reviewers only), anomaly flags,
          composition profiles, system writes, identity sealing enforcement
```

**The cardinal constraint (binding on all three):**

> The AI layer must retain zero prescriptive power. It may suggest, summarise,
> and schedule, but must never recommend a vote, edit a proposal without explicit
> human direction, prioritise one group's interests, or unilaterally alter an outcome.

No engine output triggers a governance state change without a human action in the
chain. The sole exception: the Integrity Engine applies system changes on enacted
Resolutions — but the Resolution is a human product.

---

## 1. The Inferential Engine

### 1a. Core Responsibility

Answers three questions continuously:

1. **Who** should see / be invited to this thing?
2. **What** dormain does this content belong to?
3. **What competences are underrepresented** in this Deliberation Cell's record,
   and how should the aSTF pool be biased to compensate?

Never decides whether a thing is good, important, or correct.

---

### 1b. Competence & Curiosity Vectors

```
W_u = { w_u,d }    — competence vector (0–3000 per dormain), maintained by Integrity Engine
B_u = { b_u,d }    — curiosity vector (self-declared, 0–1), zero effect on vote weight
```

`B_u` drives matching and feed surfacing only — not voting.

---

### 1c. Dormain Tagging

```
Layer 1 — Author signal (primary)
  Circle member confirms dormain(s) at sponsorship or proposal initiation.

Layer 2 — NLP classification
  Engine classifies content text. Used as default when no author signal,
  and as validation when author signal exists (mismatch → soft flag).

Layer 3 — Human correction
  Any Circle member may correct a misclassification (one-click action).
  Correction logged by Integrity Engine: who corrected, engine's original
  tag, corrected tag. Systematic errors surfaced to System Custodian Circle.
```

Tune toward recall — over-tagging is less harmful than missed routing.

---

### 1d. Commons Feed Matching

```
relevance(u, thread) = max(mandate_match(u, thread), curiosity_match(u, thread))

mandate_match = 1.0 if any of u's Circles have mandate over thread dormain
curiosity_match = b_u,d for the thread's dormain(s), range 0–1
```

**Surfacing:** `relevance = 1.0` → always surfaced; `relevance > 0.5` → surfaced
unless notification cap hit; `≤ 0.5` → accessible but not pushed.

`Sponsor as Proposal` renders only when `mandate_match = 1.0`. UI gate backed by
the engine's mandate check, not a permissions system.

The engine surfaces; it does not hide. Members can always browse the full Commons.

---

### 1e. STF Slot Matching

```
candidate_score(u, stf) =
  competence_fit(u, stf.dormains)       × [0–1]
  × curiosity_fit(u, stf.dormains)      × [0–1]
  × availability(u)                     × [0–1, inverse of current STF load]
  × independence(u, stf)                × [0 if conflict-of-interest flag, else 1]
```

**Novice reservation (default 30%):** within novice pool (`w_u,d < 800`),
ranked curiosity-first then availability. Within expert pool (70%): competence-fit first.

**Auto-scaling:** if pending issues exceed threshold, propose additional xSTF slots
to relevant Circle members as a notification. Humans approve the opening of slots.

---

### 1f. Proposal Routing

```
routing(proposal):
  tags = classify(proposal.content)
  invited = [c for c in org.circles if overlap(c.mandate_dormains, tags) > 0]
  return invited + [proposal.initiating_circle]   # initiating circle always included
```

Routing result is visible in the Cell: which Circles were invited and on what
dormain basis.

---

### 1g. Homogeneity Flag

After routing, if invited Circles share > 80% dormain overlap:
surface notification to Cell initiator suggesting a Circle with broader coverage.
Suggestion only — dismissable.

---

### 1h. aSTF Composition Balancer

When a Motion Review Sub-Cell is being constituted, the Integrity Engine provides
the Deliberation Cell's **dormain composition profile** — not just who was invited,
but what dormains are actually represented in the contributions.

The Inferential Engine applies a bias signal when scoring aSTF candidates:

```
composition_gap(cell, dormain_d) =
  max(0, target_representation_d − actual_representation_d_in_record)

astf_candidate_score(u, stf, cell) =
  base_candidate_score(u, stf)
  + Σ_d [ composition_gap(cell, d) × w_u,d_normalised ]
```

Reviewers whose competences fill the Cell's dormain gaps score higher in the
candidate pool. This is a **weighting factor, not a hard requirement** — all
eligibility criteria (independence, W_h thresholds, blind review rules) still apply.

The composition gap analysis is visible to the commissioning Circle:
*"Note: Deliberation Cell record shows low Financial competence representation.
aSTF pool biased toward reviewers with Financial W_s."*

**aSTF Revision Request:**

Beyond Approve / Reject, the aSTF may issue a **Revision Request** when composition
gaps are material to decision quality:

```
verdict options: Approve | Reject (+ rationale) | Revision Request (+ directive)
```

A Revision Request reactivates the Deliberation Cell with the aSTF's directive
attached as context. Unlike Reject, the motion is not dissolved — it returns to
deliberation with a specific instruction. Example:

> *"Deliberation record shows insufficient Financial competence relative to the
> budget implications of this motion. Recommend inviting the Budget Circle before
> resubmitting. This concern is noted in the record and will be visible to the
> next Gate 1 panel."*

The Cell may ignore the directive and resubmit anyway. The aSTF's concern is
permanently in the record. A pattern of ignored Revision Requests is itself a
signal the next panel will weigh in their process soundness assessment.

---

## 2. The Insight Engine

### 2a. Core Responsibility

Cognitive load reduction. Without it, parallel high-volume participation is not
humanly sustainable — the source framework is explicit on this.

```
1. On-demand draft proposals   — at sponsorship click, not proactively
2. Cell minutes (rolling)      — structured extraction, not transcript
3. Motion drafting             — from Cell record at crystallisation
4. Scheduling & notification   — with burnout guardrails
5. Fact-checking               — reference citations, not corrections
```

---

### 2b. On-Demand Draft Proposals

**Trigger:** the sponsor clicks `Sponsor as Proposal`. The Insight Engine reads
the current thread state at that moment and generates the draft.

Not a background process. The thread is alive — proposal generation happens when
the sponsor judges the right moment. This preserves human agency over timing and
avoids unnecessary compute on threads that may never be sponsored.

**Output:**

```
PROPOSAL DRAFT
Generated: [timestamp] from Thread #[id] (current state)

FOUNDING MANDATE:
[2–4 sentence synthesis of the thread's core argument for action]

POSITIONS IN THREAD:
[Narrative brief — contributors named in context of their positions]

OPEN QUESTIONS NOT YET RESOLVED:
— [list of unresolved tensions or unanswered questions]

SUGGESTED DORMAIN TAGS: [from Inferential Engine]
ATTRIBUTED CONTRIBUTORS: [list of @handles]
```

**Attribution — narrative form, not a citation list:**

The draft represents the debate as a structured brief. Contributors are named in
context. Example:

> *"Members broadly support reducing the novice threshold — [@jkolly, @mtracy,
> @guest8263] argue that less than 25% is adequate given current participation
> rates. @jtukei dissents, asserting that the org adopted PAAS specifically to
> maximise participation and that 35% better reflects that intent. @pahmed [OP]
> has noted it may be too early to settle this without more cycle data."*

The sponsor sees who said what before deciding whether to sponsor and what the
founding mandate should be. They may edit the draft before confirming.

**The engine does not file. A Circle member confirms and sponsors.**

---

### 2c. Cell Minutes (Rolling)

```json
{
  "cell_id": "...",
  "as_of": "...",
  "key_positions": [
    { "position": "...", "supporters": ["@handle"], "evidence_cited": ["..."] }
  ],
  "open_questions": ["..."],
  "emerging_consensus": "..." | null,
  "points_of_contention": ["..."],
  "new_context_added": [
    { "contributor": "@handle", "summary": "...", "source": "commons | direct" }
  ]
}
```

Visible to all Cell participants. Raw Cell record remains primary.

---

### 2d. Motion Drafting

At crystallisation, engine drafts from Cell record per motion type (OrbSys_v7.md §20):

| Motion Type | Engine Output |
|---|---|
| System-bound | Extracts parameter changes, populates specification fields, flags out-of-range values for Integrity Engine pre-validation |
| Non-system | Synthesises directive statement, identifies commitments, flags ambiguities |
| Hybrid | Drafts both blocks independently; flags accountability clauses for explicit confirmation |

Circle members review and may edit before filing.

---

### 2e. Scheduling & Notification

**Deadline ladder:**
```
T−7 days → soft reminder
T−3 days → urgent reminder
T−1 day  → critical alert (member + Circle lead)
T=0      → missed deadline flag to Circle (no automatic action)
```

**Notification caps (default, configurable):**
```
max 12/day, max 3/hour

P1 (always, no cap): STF deadline < 24h, vote closing < 2h, judicial flag
P2 (subject to cap): Cell invitation, thread sponsored in your dormain, slot opened
P3 (digest only):    Curiosity-match activity, Circle health, parameter changes
```

---

### 2f. Fact-Checking

If a Cell contribution contradicts an enacted Resolution or known parameter value,
the engine surfaces a soft reference: *"Note: Resolution ORG-024-006 states X."*

Reference, not correction. Cites; does not judge.

---

### 2g. What the Insight Engine Does Not Do

```
— Does not recommend how to vote
— Does not proactively generate draft proposals
— Does not decide when a Cell has reached consensus
— Does not rate contribution quality
— Does not generate the official Cell record
— Does not read blind review Cell content (Integrity Engine enforces isolation)
```

---

## 3. The Integrity Engine

### 3a. Core Responsibility

```
1. Tamper-evident ledger        — append-only, all governance events
2. ΔC computation               — formal reviewers only (v1.0)
3. Anomaly detection            — flags for human investigation, never acts
4. System write enforcement     — enacted Resolutions only; composition profiles;
                                  identity sealing; M_cmp management
```

---

### 3b. The Competence Change Formula (ΔC)

```
ΔC_u,d = G · K_u,d · Σ_r∈R [(S_r − 0.5) · w_r,d · M_r,d]
                      ─────────────────────────────────────
                              Σ_r∈R [w_r,d · M_r,d]
```

| Symbol | Name | Values |
|---|---|---|
| `G` | Activity Gravity | 0.5 informal/Commons, 1.0 formal motion/deliberation, 1.2 audit/formal test |
| `K_u,d` | Volatility | 60 new, 30 established, 10 veteran — per user per dormain |
| `S_r` | Reviewer Score | 0.0 → 0.5 (neutral) → 1.0 |
| `w_r,d` | Reviewer competence in dormain | 0–3000 |
| `M_r,d` | Circle Multiplier | 1.6 direct Circle member, 1.2 related Circle, 1.0 unrelated |

**v1.0 scope: formal reviewers only.**
`R` = the set of formal reviewers assigned to the activity:
- STF work: the STF member reviewers (aSTF, vSTF, jSTF)
- Commons posts: Circle members who perform a designated formal review action

Casual reactions and upvotes do not generate ΔC in v1.0. Every ΔC event has
a named, accountable reviewer set in the ledger.

**Endorsement provenance** (optional reason + link per reviewer score) — available
as optional metadata in v1.0, not required. Full provenance weight mechanics deferred
to v1.1.

**Caps:**
```
C_max   = 120 pts   — maximum ΔC per activity
T_audit = 50 pts    — held as pending_audit, Org Integrity Circle notified
```

---

### 3c. Volatility (K) Progression

```python
def compute_K(user, domain):
    proof_count = user.formal_review_events_in(domain)
    time_active  = user.months_with_activity_in(domain)
    if proof_count < 5 or time_active < 3:   return 60
    elif proof_count < 20 or time_active < 12: return 30
    else:                                      return 10
```

---

### 3d. W_h and the Initial Boost

```
on successful vSTF verification:
  W_h_u,d = verified_value                      # static
  W_s_u,d = max(W_s_u,d, W_h_u,d)              # boost W_s to credential level
  # W_s then decays independently if member stops contributing
```

`W_h` gates eligibility (jSTF, W_h-minimum Circles). Does not directly vote.

---

### 3e. Decay — Domain-Defined, Circle-Governed

Each dormain's decay function and rate is a **governed parameter** set by the
Circle with mandate over that dormain via standard sys-bound motion.

**Default (until a Circle customises via motion):**
```
function:   exponential
half_life:  12 months
floor:      0.3 × W_s_peak   # competence doesn't fully decay to zero
```

```
W_s_u,d_decayed = W_s_u,d × decay_factor(dormain_d, time_since_last_activity)

decay_factor(dormain, t) = enacted_decay_fn(dormain).apply(t)
# falls back to default exponential if no Resolution has been enacted for this dormain
```

Engineering decays faster than History, which decays differently from Pop Culture.
The Circle with mandate over the dormain governs how. The Integrity Engine applies
whatever is enacted.

**Transfer coefficients: deferred to v1.1.** Dormains treated independently in v1.0.

---

### 3f. The Tamper-Evident Ledger

Append-only. No entry is ever modified. Corrections are new entries referencing
the entry they supersede.

**Event types:**

```
governance:
  cell_created | cell_state_change | cell_dissolved | cell_archived
  cell_composition_profile_computed
  commons_thread_created | thread_sponsored | thread_frozen
  motion_filed (type: sys-bound | non-system | hybrid)
  vote_cast (member_id, weighted_score, dormain, cell_id)
  stf_verdict_filed     (reviewer_id: SEALED — permanent default)
  revision_request_issued (astf_id: SEALED, directive, cell_id)
  resolution_created | resolution_status_change
  system_parameter_change (parameter, old_value, new_value, resolution_id)

competence:
  delta_c_applied (member_id, dormain, delta, reviewer_set, activity_id)
  delta_c_pending_audit (member_id, dormain, delta, trigger)
  wh_verified | wh_boost_applied
  competence_decay_applied (member_id, dormain, ws_before, ws_after, fn_used)

oversight:
  anomaly_flag (type, subject, severity, trigger)
  member_state_change (from_state, to_state, trigger)
  mcmp_freeze | mcmp_restore
  stf_identity_unsealed (condition: malpractice | judicial_penalty, ruling_id)

structural:
  circle_created | circle_dissolved | circle_membership_change
  org_parameter_change
```

---

### 3g. STF Identity Sealing (Permanent Default)

All STF reviewer identities are permanently sealed in the record. Not a temporary
state pending review — the permanent default.

**Two unsealing conditions only:**

```
1. Malpractice finding by later aSTF:
   A subsequent aSTF review finds evidence of malpractice by a specific reviewer.
   Identity disclosed as part of the malpractice finding in the judicial record.
   Revealed in context of the finding, not as standalone disclosure.

2. jSTF penalty on a named individual:
   A jSTF investigation levies a specific sanction on a named individual for
   conduct during an STF process.
   Identity disclosed in the judicial ruling, linked to the ruling.
```

**No voluntary disclosure** — not available to reviewers in v1.0. Voluntary
disclosure creates implicit social pressure on other reviewers to account for
themselves, undermining panel independence.

*Voluntary disclosure as a governance option (via Governance Circle motion) may
be introduced in a later version. PAAS authorship strongly discourages it.*

**Closed Circle Cell records** follow the same rule — remain closed; readable
only by periodic aSTF and jSTF on mandate. Not openable by motion, resolution,
or voluntary action.

---

### 3h. Cell Composition Profile

Computed by the Integrity Engine when an aSTF pool is being constituted.
Feeds the Inferential Engine's composition balancer (§1h).

```
composition_profile(cell):
  for each contribution c in cell.record:
    for each dormain d of c.author's competences:
      weighted_d += w_author,d × contribution_weight(c)
  normalise to percentages across all dormains represented

contribution_weight(c) = length_normalised × recency_weight
```

Logged as `cell_composition_profile_computed`. Visible to the commissioning Circle.

---

### 3i. Anomaly Detection

Monitors continuously. Flags for human investigation. Never acts autonomously.

| Type | Trigger | Response |
|---|---|---|
| Competence spike | `\|ΔC\| > 50 pts` single activity | Hold as `pending_audit`, notify Org Integrity Circle |
| Auditor-auditee correlation | Statistical pattern of favourable/unfavourable scores toward specific member/Circle across STF instances | Flag to Judicial Circle |
| Sybil-like pattern | Correlated voting, improbable competence curves | Flag to Org Integrity Circle; M_cmp freeze pending investigation |
| Vote weight concentration | Single member exceeds configured % of total deliberation weight | Notify Insight Engine to surface participation-breadth flag to Cell — no vote invalidated |
| Gate 2 diff failure | Applied value ≠ Resolution-specified value | Automatic Contested status; block related parameter changes; notify System Custodian + originating Circle |

---

### 3j. Blind Review Isolation (Data Layer)

```
on Motion Review Sub-Cell creation:
  for each reviewer r:
    create isolated_view(r):
      content = [motion_text, deliberation_record, commons_snapshot]
      write_access = own verdict only
      read_access  = own view only
      identity     = absent from all shared records
  cross_reviewer_communication: BLOCKED at data layer
  reviewer_list: not queryable by any reviewer

on all_verdicts_filed:
  identities REMAIN SEALED (permanent default, see §3g)
  aggregate_verdicts()
  publish aggregated result to org archive
  individual identities published only if unsealing conditions met
```

---

### 3k. M_cmp Freeze / Restore

```
on integrity_flag(member):
  member.M_cmp = frozen; member.voting_weight = suspended; state = "Under Review"

on investigation_resolved:
  cleared   → restore M_cmp, restore voting_weight, state = "Active"
  sanctioned → apply_sanctions_per_judicial_ruling()
```

Both events logged. Visible in audit archive.

---

### 3l. System Write Enforcement

```
on resolution_enacted:
  if sys-bound:
    begin_atomic_transaction():
      for each (parameter, new_value) in spec:
        assert pending_value(parameter) == new_value   # Gate 2 diff
        system.write(parameter, new_value)
        log: system_parameter_change(...)
    if success: resolution.status = "Enacted_Locked"
    if any fail: rollback_all(); resolution.status = "Contested"
                 notify System_Custodian + originating_circle
```

Atomic — all parameters in the spec apply together or none do.

---

## 4. Service Boundary Model

```
                    ┌─────────────────────────────────────────┐
                    │            HUMAN ACTIONS                │
                    │  (vote, sponsor, file report, confirm)  │
                    └──────┬────────────────────┬────────────┘
                           │                    │
                    ┌──────▼──────┐    ┌────────▼────────┐
                    │  INFERENTIAL │    │     INSIGHT      │
                    │   ENGINE    │    │     ENGINE       │
                    │  routing    │    │  on-demand draft │
                    │  tagging    │    │  cell minutes    │
                    │  matching   │◄───│  motion draft    │
                    │  feed       │    │  schedule/notify │
                    │  aSTF bias  │    │  fact-check      │
                    └──────┬──────┘    └────────┬─────────┘
                           │                    │
                    ┌──────▼────────────────────▼─────────┐
                    │           INTEGRITY ENGINE           │
                    │  append-only ledger                  │
                    │  ΔC (formal reviewers only, v1.0)    │
                    │  cell composition profiles → IE      │
                    │  anomaly detection & flagging        │
                    │  system writes (enacted res. only)   │
                    │  blind review isolation              │
                    │  STF identity sealing (permanent)    │
                    │  M_cmp freeze / restore              │
                    └──────────────────────────────────────┘
```

**Key rules:**
- Inferential Engine reads competence vectors and receives composition profiles
  from the Integrity Engine ledger. Does not write competence.
- Insight Engine reads Cell content and ledger events. No access to blind review
  Cell content. Does not write governance state.
- Integrity Engine does not read from the other two. It receives governance events
  directly and outputs signals (composition profiles, anomaly flags) the other
  engines may consume.
- Communication between engines flows via the shared event ledger (pub/sub).
  No engine queries another engine's internal state.

---

## 5. v1.0 Deferred Features

| Feature | Deferred to |
|---|---|
| Endorsement provenance (reason + link, weighted) | v1.1 |
| Transfer coefficients (cross-dormain competence) | v1.1 — requires dormain hierarchy definition |
| Voluntary STF identity disclosure (governance option) | Later version; PAAS authorship strongly discourages |

---

*Engine Trinity v2 — compiled alongside OrbSys v7.*
*Next: data model sketch — Cell, Commons thread, motion schema, competence ledger
entry, composition profile.*
