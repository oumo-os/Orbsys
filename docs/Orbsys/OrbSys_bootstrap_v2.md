# Orb Sys — Onboarding & Bootstrapping Flow
## v2

> How an org comes into existence. The PAAS bootstrapping insight: STFs
> can exist before Circles or Cells. The only prerequisite is competence
> weights. The bootstrap sequence uses the system's own native mechanisms
> from step one — no suspended governance, no special authority mode, no
> ratification ceremony that bypasses normal process.
>
> Cross-reference: OrbSys_v7.md, OrbSys_engines_v2.md,
> OrbSys_datamodel_v1.md, OrbSys_api_v1.md

---

## The Core Insight

The bootstrapping problem in most governance systems is:
> *You need working governance to ratify governance.*

PAAS dissolves this by separating the question. Governance authority flows
from **competence weights**, not from Circles. Circles require competence
weights to function — but competence weights do not require Circles to exist.

This means the STF mechanism is available from the moment the first member
submits a competence proof. The vSTF can operate on day one, before a single
Circle has been formed. The bootstrap sequence uses this property deliberately:
competence is verified first, Circles are formed second, and the founding
deliberation inherits a working audit baseline from the moment it opens.

---

## The Eight-Step Sequence

```
Step 1 — Org Identity
Step 2 — Domain Templates
Step 3 — Member Registration & Proof Submission
         [Engine computes preliminary weights]
         [vSTF pool forms, peer-verifies weights]
Step 4 — Founding Circle Selection
Step 5 — Founding Deliberation
         [aSTF baseline already exists from Step 3]
Step 6 — Founding Resolution → Founding Circle Dissolves → Locked
Step 7 — Competence Re-evaluation + New Circle Population
Step 8 — Pilot Closes → Normal Operations
```

---

## Step 1 — Org Identity

**Actor:** one or more initiating members (no special authority — they are
the first members of the initial pool).

**Actions:**

```
POST /admin/orgs
Body: {
  name, slug, purpose, founding_tenets_draft,
  commons_visibility: 'members_only'
}
```

The org exists. The ledger is initialised. `bootstrapped_at = null` — not
because governance is suspended, but because the founding resolution has
not yet been filed. The system is live and operational in all respects.

**Founding tenets draft** is the initiating members' proposed statement of
purpose and values. It is a draft — subject to revision during Step 5.
It is recorded in the ledger immediately as a provisional document, not
yet a Resolution.

---

## Step 2 — Domain Templates

**Actor:** initiating members, with input from the early joining pool.

Orb Sys provides a library of **Domain templates** — pre-defined Dormain
sets for common org types (open-source project, research collective, DAO,
cooperative, professional association, etc.). Each template carries:

```
template fields:
  — dormain names and descriptions
  — suggested decay policies per dormain
  — suggested Circle structures that map to the dormains
  — suggested W_h credential types per dormain
```

The initiating members select the closest template and adjust it to their
org's actual shape. Dormains can always be revised later through normal
governance motions — the template is a starting point, not a commitment.

```
POST /{org}/admin/dormains (batch)
Body: [{ name, description, decay_fn, decay_half_life_months,
         decay_floor_pct, source: 'template' | 'custom' }]
```

**No Circles are defined yet.** Dormains exist; Circles do not. This is
intentional — the Circle structure will emerge from the founding deliberation
in Step 5, informed by the competence distribution revealed in Step 3.

**Inferential Engine** begins training its NLP classifier on the Dormain
labels immediately. Dormain tagging is live from this point.

**Ledger state after Step 2:**
```
event 1: org_created      { org_id, name, slug, purpose }
event 2: dormain_created  { dormain_id, name, decay_defaults }  ×N
```

---

## Step 3 — Member Registration & Proof Submission

This is the operative step that makes the rest of the bootstrap work.
It has two concurrent sub-processes: **proof submission** and **vSTF
peer-verification**, which run simultaneously from the moment the first
members register.

---

### 3a. Registration

**Actor:** all founding and initial members.

```
POST /{org}/admin/members/invite (batch) OR
GET  /{org}/join/:invite_token  (self-registration if open)

On joining:
  member.current_state = 'probationary'
  W_s = 0 across all dormains   (no scores yet)
  K   = 60 (new user)
  B_u = {} (curiosity not yet declared)
```

Members are immediately invited to:
1. Declare curiosity vectors (B_u) — unlocks feed relevance
2. Submit competence proofs (W_h claims) — triggers the vSTF pool

---

### 3b. Proof Submission

Members submit W_h credential claims for any Dormain where they hold
verifiable external credentials:

```
POST /{org}/competence/wh-claims
Body: {
  dormain_id,
  credential_type,    — degree | certification | patent | license | verified_contribution
  value_claimed,
  vdc_reference       — Verifiable Digital Credential reference
}
```

Members may submit multiple claims across multiple Dormains simultaneously.
There is no wait period — submissions are accepted as they arrive.

**The Integrity Engine computes preliminary W_h values** from the claims
before peer verification. These are `wh_preliminary` status — not yet
enacted, but used immediately to seed the vSTF pool in Step 3c.

The preliminary computation is straightforward:

```
preliminary_W_h(member, dormain) =
  credential_type_base_value[credential_type]
  × claimed_value_scaling_factor
  — both conservatively floored pending verification
```

**Why preliminary values before verification?**
The vSTF that will verify these claims needs reviewers with competence
in the relevant Dormain. The only source of that competence, at this stage,
is the other members' preliminary W_h values. The preliminary scores are
used exclusively to form the vSTF pool — they carry no governance weight
until verified.

---

### 3c. vSTF Peer Verification (Pool Self-Verification)

This is the structural insight. The vSTF is commissioned immediately, from
the initial membership pool, to verify the initial membership's own claims.

```
vSTF formation logic (Inferential Engine):
  for each pending W_h claim (member M, dormain D):
    candidate_pool = members with preliminary_W_h > 0 in dormain D
                     excluding member M (cannot verify own claim)
    assign 2–3 reviewers from candidate_pool
    (blind parallel, isolated view tokens, same process as any vSTF)
```

**The pool is verifying itself.** This is not circular — it is the same
logic as any peer review system. A physicist's credentials are reviewed by
other physicists. The preliminary scores are enough to identify who has
relevant expertise to verify whom. The verification process then either
confirms, adjusts, or rejects each claim, producing the enacted W_h value.

**Blind parallel isolation** is enforced by the Integrity Engine from the
first vSTF — exactly as it would be in live operations. No exceptions for
bootstrapping. The process is identical to any vSTF that will ever run in
this org.

Each verified claim produces:
```
→ event: wh_verified       { member_id, dormain_id, value, vstf_id }
→ event: wh_boost_applied  { member_id, dormain_id, ws_before: 0, ws_after: verified_value }
```

W_s is boosted to the verified W_h value. The member's competence is now
in the ledger, immutably, as a proper enacted record — not a provisional
bootstrap artefact.

---

### 3d. The aSTF Baseline Emerges

As vSTF reports come in and W_h values are enacted, the org now has
a **working competence pool**. This pool is sufficient to form aSTFs.

The aSTF requires reviewers with W_s in the relevant Dormains. After Step 3c,
those reviewers exist. The founding deliberation in Step 5 will therefore
not operate in a governance vacuum — it operates with a functional aSTF
layer available from the moment deliberation begins. No bootstrap exception
needed for Gate 1.

**Ledger state after Step 3:**
```
event 3+: wh_claim_submitted   { member_id, dormain_id, value_claimed } ×P
event N+: vstf_commissioned    { stf_id, dormain_id, reviewer_ids: SEALED } ×Q
event M+: stf_verdict_filed    { stf_id, assignment_id } ×R (sealed)
event K+: wh_verified          { member_id, dormain_id, value } ×S
event L+: wh_boost_applied     { member_id, dormain_id, ws_after } ×S
```

All events are real ledger events. No setup-mode exceptions. No labels
distinguishing bootstrap events from operational events — the ledger does
not know or care that this is the org's first week.

---

## Step 4 — Founding Circle Selection

**Actor:** initiating members, with reference to the verified competence
distribution from Step 3.

The Founding Circle is a **temporary, manually-selected** body. Its mandate
is specific and bounded: deliberate on the org's desired governance structure,
produce the founding resolution, and dissolve.

**Selection basis:**

```
MANUALLY SELECTED, reflecting two criteria:
  1. Prior organisational structure and trust relationships
     — who held meaningful responsibility before Orb Sys?
     — whose authority does the community already recognise?
     — this provides continuity and legitimacy during the transition

  2. The verified competence distribution from Step 3
     — selection should reflect breadth across Dormains
     — avoid heavy concentration in one Dormain
     — the Inferential Engine surfaces the homogeneity warning
       if selection is too narrow
```

This is not a Circle in the ongoing governance sense — it has no mandate
Dormains, no ongoing role, no audit obligations. It is a temporary deliberative
body that exists solely to produce one founding resolution. The data model
represents it as a Circle with a special flag:

```sql
circles.founding_circle = true   — this circle dissolves on founding resolution enactment
circles.mandate_dormains = []    — no ongoing mandate; not routable by Inferential Engine
```

**Size:** typically 5–15 members depending on org size. Large enough to
represent the community's key perspectives; small enough to deliberate efficiently.

**No Circle members who are not in the founding pool.** The Founding Circle
is a subset of the members who have already registered and submitted proofs
in Step 3. It is not appointed from outside.

---

## Step 5 — Founding Deliberation

**Actor:** Founding Circle, with Commons open to all registered members.

The Founding Circle opens Deliberation Cells for the org's key structural questions.
All registered members can read and contribute to Commons. The Founding Circle
members have write access to Cells as the responsible deliberating body.

**The aSTF is operational from day one of this step** (Step 3 established the
competence pool). Gate 1 applies to any motion filed during founding deliberation
— no exceptions. The founding deliberation is not exempt from oversight.

---

### 5a. Founding deliberation streams

```
STREAM 1: Dormain Refinement
  — Are the template-derived Dormains correct for this org?
  — Do the decay policies fit the org's knowledge half-life reality?
  — Are there gaps, overlaps, or misnamings?
  — Output: revised Dormain set (sys-bound motion if changes from Step 2 defaults)

STREAM 2: Circle Architecture
  — What Circles should govern this org?
  — Which Dormains does each Circle hold mandate over?
  — What minimum W_h thresholds apply to each Circle?
  — What is the relationship between Circles (overlapping mandates)?
  — Output: Circle definitions + mandates (non-system motion, directive form)

STREAM 3: Governance Parameters
  — What overrides from org defaults fit this community?
  — novice_slot_floor_pct, rotation_window, notification caps, W_h thresholds
  — Decay policy per Dormain (if different from template defaults)
  — Output: parameter override set (sys-bound motion)

STREAM 4: Founding Tenets Finalisation
  — Review and confirm the Step 1 draft
  — Resolve any tensions surfaced in registration and early discussions
  — Output: enacted founding tenets (non-system motion, marked immutable)
```

**Each stream produces one or more motions.** Each motion goes through the
full lifecycle — Deliberation Cell → crystallise → file → aSTF Gate 1 →
Resolution. No stream is exempt. The founding deliberation is live governance,
not a special pre-governance period.

**Unresolved tensions** are not blocked — they are recorded. If a stream
produces a motion that the aSTF issues a Revision Request on, the Cell
reactivates with the directive attached. The founding deliberation may
take longer if composition gaps are identified and new perspectives are
needed. This is the system working correctly.

---

### 5b. What the aSTF is reviewing during founding deliberation

During founding deliberation, the aSTF has a specific additional lens —
in addition to the standard process quality checks:

> *Is this motion consistent with the org's founding tenets draft?*
> *Does it reflect the interests of the full registered membership, or
> primarily the interests of the Founding Circle members?*

This is the founding-specific composition concern. The aSTF pool for founding
deliberation motions should be biased toward members who are **not** in the
Founding Circle — they provide the independent voice that the Founding Circle,
by definition, cannot provide about its own proposals.

The Inferential Engine applies this bias automatically:

```
for founding deliberation motions:
  composition_bias_signal += heavy weight toward
    registered members NOT in founding_circle
    (independence criterion, same logic as auditor-auditee separation)
```

---

## Step 6 — Founding Resolution → Founding Circle Dissolves → Locked

**The single most consequential event in the org's lifecycle.**

When the founding deliberation streams have all produced enacted Resolutions
(all Cells closed, all Gate 1 approvals filed, all parameter changes validated),
the Founding Circle files the **Founding Resolution** — a single capstone
resolution that:

```
FOUNDING RESOLUTION CONTENT:
  §1  Reference to all founding motions (by resolution ID)
  §2  Declaration that the founding deliberation is complete
  §3  Instruction to the Integrity Engine:
        — dissolve the Founding Circle
        — populate new Circles from the registered membership per Circle architecture
        — run competence re-evaluation (Step 7)
        — set bootstrapped_at = NOW()
  §4  Constitutional amendment threshold:
        — founding tenets require N% supermajority to amend
        — suggested: 75%, set as a sys-bound parameter
```

**The Founding Resolution itself goes through Gate 1.** The aSTF reviews it
for completeness — are all founding streams represented? Are there unresolved
Revision Requests pending? Is the dissolution instruction consistent with what
was deliberated?

On Gate 1 approval and enactment:

```
Integrity Engine executes atomically:
  1. founding_circle.dissolved_at = NOW()
  2. founding_circle.dissolution_resolution_id = <founding_resolution_id>
  3. org.bootstrapped_at = NOW()
  4. All founding Circle members revert to their competence-score-determined
     roles in the new Circle architecture (no special status retained)
  5. → event: circle_dissolved { founding_circle_id, reason: 'founding_resolution' }
  6. → event: org_bootstrapped { org_id, bootstrapped_at }
```

**No backtracking.** The founding resolution is `enacted_locked`. The founding
Circle's dissolution is immediate and complete. No member of the founding Circle
has any authority derived from that role after this event. They are ordinary
members with ordinary competence scores and ordinary Circle memberships
(if they qualify for the new Circles per the enacted architecture).

**Why the Founding Circle must dissolve completely:**
The founding tenets mandate is specific to governance inception. Allowing the
founding Circle to persist — even in advisory form — creates a de facto
founding class with accumulated informal authority. The dissolution is the
org's structural commitment that legitimacy flows from ongoing contribution,
not from having been present at creation.

---

## Step 7 — Competence Re-evaluation & Circle Population

**Triggered immediately** by the Founding Resolution enactment.

### 7a. Competence re-evaluation

The vSTF was operating at high volume during Steps 3–6. Step 7 is a focused
re-evaluation pass: any W_h claims that were pending when the founding
resolution was enacted are prioritised and resolved. Any preliminary W_h values
that have not yet been through full vSTF verification are flagged as
`pending_final_verification` — they cannot be used for jSTF eligibility or
W_h-gated Circle membership until fully verified.

```
on org_bootstrapped:
  → Inferential Engine: flag all members with wh_preliminary status
  → Commission accelerated vSTF batch for outstanding claims
  → Priority: claims in Dormains where new Circles require W_h minimums
```

Additionally, W_s scores from any vSTF or aSTF participation during Steps
3–6 are now fully applied. Members who reviewed their colleagues' credentials
during Step 3, or who participated in aSTF reviews during Step 5, have earned
ΔC through that formal review work. The Integrity Engine applies all queued
ΔC events at bootstrap.

### 7b. New Circle population

New Circles are populated from the registered membership based on:

```
CIRCLE MEMBERSHIP DETERMINATION:
  1. W_h minimums (if the Circle's founding resolution set any)
     → members below the minimum are not eligible for that Circle
  2. W_s in the Circle's mandate Dormains
     → Inferential Engine sorts by competence fit
  3. Prior organisational role (reflected in the manual selection context
     during Step 4 — members who held responsibility in the equivalent
     prior role are surfaced as candidates)
  4. Self-declaration of interest (B_u curiosity signal for the Dormains)

PROCESS:
  The Inferential Engine produces a ranked candidate list per Circle.
  Existing Circle members (from founding deliberation participants who
  qualified) review and confirm the roster via a lightweight Circle vote.
  This is the first live Circle vote in the org's governance history.
```

**System operations start immediately** as each Circle is populated. A Circle
does not need to wait for all other Circles to be populated before it can begin
its governance work. The moment a Circle has its minimum quorum of members,
it is live:

```
on circle_member_added (reaching quorum):
  circle.state = 'active'
  → Inferential Engine: begin routing proposals to this Circle
  → Insight Engine: begin surfacing this Circle's Dormain content to members
  → aSTF pool: this Circle's members are now eligible for relevant aSTF roles
```

The org reaches full operational capacity as Circles populate — typically
within hours to days of the founding resolution, not weeks.

---

## Step 8 — Pilot Closes → Normal Operations

The "pilot" in this model is not a bounded scope restriction. It is simply
the **period between first Circle population and stable operational rhythm**.
It has no formal end date and no governance exception — it is normal operations
from day one, just with a community that is still learning the system.

**What "pilot closes" means practically:**

```
PILOT PERIOD SIGNALS (not a hard boundary):
  — All Circles have reached quorum and are active
  — First full motion lifecycle completed (Commons → Resolution → enacted)
  — First periodic aSTF cycle completed for at least one Circle
  — Parameter tuning motions filed and enacted based on early experience
  — New member onboarding flow is working (new members gaining W_s through
    Commons formal reviews and xSTF participation)
  — No anomaly flags outstanding

PILOT CLOSES WHEN:
  The Org Integrity Circle (or equivalent) determines that operations are
  stable — this is a governance judgment, not a system state.
  It may issue a simple non-system Resolution: "Pilot phase complete —
  normal operations declared." This is a milestone, not a mode change.
  The system does not change behaviour at this point; it records that
  the community has assessed itself as operational.
```

---

## Member Onboarding (Ongoing, Post-Bootstrap)

Once `bootstrapped_at` is set and Circles are populated, new member
onboarding follows the standard flow:

### Registration → Curiosity → Contribution → Circle

```
1. REGISTRATION
   Member joins (invite or open application per Membership Circle policy).
   state = 'probationary', W_s = 0, K = 60.
   Proof-of-personhood check per org policy.

2. CURIOSITY DECLARATION
   Member declares B_u vector.
   Feed relevance immediately active.
   Inferential Engine surfaces starter Commons content in top-curiosity Dormains.

3. COMMONS CONTRIBUTION
   Probationary member can post in Commons.
   Circle member formal reviews generate ΔC events.
   K = 60 means W_s climbs quickly with genuine contribution.

4. W_h CLAIM (any time)
   Member submits credential claims.
   vSTF commissioned (same blind-parallel process as Step 3c of bootstrap).
   W_s boosted to verified W_h on enactment.

5. xSTF PARTICIPATION
   Once W_s > 100 in any Dormain, member eligible for novice xSTF slots.
   Inferential Engine surfaces slots in curiosity-matched Dormains.
   xSTF participation (G = 1.0) is the primary accelerator for W_s growth.

6. CIRCLE MEMBERSHIP
   Invited by existing Circle member, confirmed by Circle vote.
   Transition: K begins moving toward 30 (established) as proof_count grows.
   M_cmp = 1.6 for primary Dormains, 1.2 for related.
   Full governance participation unlocked.
```

**The onboarding funnel is the same mechanism as Step 3c.** A new member
who joins after bootstrap goes through exactly the same vSTF peer-verification
for W_h claims as the founding members did. There is no distinction in the
ledger between a founding member's W_h record and a post-launch member's W_h
record. The process is uniform from day one.

---

## Bootstrap State Machine (Revised)

```
ORG CREATION
  org_id created
  bootstrapped_at = null
  dormains defined from templates
  Inferential Engine NLP: ACTIVE
  ledger: LIVE
        ↓
STEP 3: MEMBERSHIP POOL FORMS
  members register
  W_h proofs submitted
  vSTF pool formed and operating
  W_s scores emerging
  aSTF capability: AVAILABLE
        ↓
STEP 4: FOUNDING CIRCLE SELECTED
  (subset of registered pool, manual)
  founding_circle.is_active = true
        ↓
STEP 5: FOUNDING DELIBERATION
  motions through full lifecycle
  aSTF Gate 1: ENFORCED
  all registered members can contribute via Commons
        ↓
STEP 6: FOUNDING RESOLUTION ENACTED
  founding_circle.dissolved
  bootstrapped_at = NOW()
  system fully locked — no backtracking possible
        ↓
STEP 7: CIRCLES POPULATE
  W_h re-evaluation ongoing
  Circles activate as quorum reached
  System ops: LIVE (per Circle, as populated)
        ↓
STEP 8: PILOT CLOSES (governance judgment)
  Org Integrity Circle declares normal ops
  No system state change — milestone record only
        ↓
[NORMAL OPERATIONS — ongoing]
```

---

## What This Design Removes

Compared to traditional bootstrap approaches:

```
REMOVED:
  × Setup mode / suspended governance
  × Special founding authority not derived from competence
  × Pre-ratification period exempt from normal process
  × Ratification ceremony that bypasses Gate 1
  × Pilot as a scope restriction (separate governance tier)
  × Any point where the system's native mechanisms are not in use

RETAINED:
  ✓ Manual Founding Circle selection (continuity with prior structure)
  ✓ Temporary nature of founding authority (dissolves completely)
  ✓ Conservative competence starting point (preliminary values before verification)
  ✓ Founding tenets immutability (constitutional amendment threshold)
  ✓ Full ledger record from event 1 (no informal pre-ledger period)
  ✓ aSTF oversight of founding deliberation (no exemptions)
```

The system's legitimacy comes from consistent application of its own rules.
A bootstrapping exception — however well-intentioned — is a founding weakness
that sophisticated actors can later exploit as precedent.

---

*Onboarding & Bootstrapping Flow v2 — corrected to use PAAS-native STF
mechanism as the bootstrapping primitive.*
*Next: agent-based simulation parameters — stress-testing governance model
and parameter choices before a real community goes live.*
