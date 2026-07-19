# Interpreting PAAS for Technical Realities

> Where Orb Sys extends, operationalises, or deliberately departs from the PAAS
> paper — and the reasoning behind each decision.
>
> The paper is a governance framework, not a software specification. Every
> implementation must resolve questions the paper leaves open. This document
> records those resolutions so they can be revisited as the system matures.

---

## 1. aSTF verdict: binary becomes three-option

**Paper:** *"The aSTF renders a final, binding decision with two possible outcomes: Approve [or] Reject."*

**Orb Sys:** A third verdict — `revision_request` — reactivates the Deliberation Cell with a specific directive attached, rather than dissolving it. The aSTF identifies what is missing and sends the motion back with instructions.

**Why:** The paper's binary model is clean and preserves the principle that each submission is a fresh audit with a fresh panel. In practice, most rejected motions fail for a correctable reason — a missing evidence base, an underrepresented Dormain, an ambiguous directive. Forcing full re-deliberation for every such case adds friction without adding scrutiny. The revision request keeps the accountability trail intact (the directive is permanently in the ledger and visible to the next Gate 1 panel) while avoiding unnecessary churn. Teams considering a strict binary model should note: the revision path can be disabled by configuring the aSTF to only use Approve / Reject.

---

## 2. Novice slot floor: xSTFs only becomes all STFs

**Paper:** *"A minimum of 30% of slots in xSTFs are reserved for users with domain competence below 800."* The restriction is explicitly scoped to xSTFs.

**Orb Sys:** The floor applies to all STF types including aSTFs and vSTFs.

**Why:** Applying the floor to aSTFs is a trade-off. The paper emphasises competence and independence for audit bodies — a novice reviewer on an aSTF could dilute audit quality. The counter-argument, which Orb Sys takes, is that aSTF participation is itself a primary mechanism for novices to earn W_s (G = 1.2, the highest gravity weight), and excluding them from audit roles creates a two-tier system where only established members can access the highest-value participation slots. The 30% floor is a minimum, not a target — in small orgs, the floor may be unreachable without compromising competence requirements, and the engine handles this gracefully by drawing from the best available pool.

---

## 3. Gate 2 as a formalised mechanism

**Paper:** Describes post-implementation audit informally — xSTF reports are submitted to an aSTF for approval, and deviations from the resolution are noted. No specific mechanism is defined for how parameter changes are verified, what happens on a mismatch, or what states a resolution passes through.

**Orb Sys:** Gate 2 is a formalised second checkpoint. For `sys_bound` motions, the Integrity Engine runs an automated diff — applied parameter values must exactly match the resolution specification, and any mismatch puts the resolution into `Contested` with full atomic rollback. For `non_system` motions, an interpretive aSTF assesses whether implementing Circles executed the directive faithfully.

**Why:** Without a mechanised verification step for parameter changes, an org's parameter values can drift from its recorded resolutions — making the ledger untrustworthy as a source of truth. The atomic rollback guarantee for sys_bound motions is the strongest version of "either the resolution is enacted as written, or nothing changes." The paper's intent — that governance decisions are faithfully implemented — requires this kind of enforcement in software.

---

## 4. Three motion types

**Paper:** Describes motions as producing Resolutions implemented by Circles. Does not distinguish between decisions that change system parameters and decisions that direct human action.

**Orb Sys:** Three types: `sys_bound` (parameter changes, Integrity Engine executes), `non_system` (directive to named implementing Circles, interpretive Gate 2), `hybrid` (both). Filing a `non_system` motion without naming implementing Circles returns a 422 — a directive with no named responsible body is rejected at the API layer.

**Why:** A software system needs to know which decisions it should enforce automatically and which require human execution. The paper's model assumes Circles implement faithfully; the taxonomy is the mechanism that makes the distinction explicit. The `implementing_circle_ids` requirement operationalises the paper's accountability principle: *"the decision-makers are also the implementers"* — if they are not, the implementing Circles must be named before the motion is filed, not discovered after it fails to be executed.

---

## 5. Commons as a named, structured space

**Paper:** References an open discussion space and sponsorship as the filter that converts discussion into formal governance. Does not name the space, specify its structure, or define a feed model.

**Orb Sys:** The Commons is a fully specified feature — threaded posts, Dormain tagging by the Inferential Engine, relevance-ranked feed using `max(mandate_match, curiosity_match)`, configurable public/private visibility, and a two-step sponsorship flow (draft → confirm).

**Why:** The paper's concept of an open space where ideas form before entering governance is sound but underspecified for implementation. The key design decision is the relevance ranking formula: Circle members see threads relevant to their mandate first, while Curiosity ensures passionate non-experts also surface relevant content. The sponsorship two-step (Insight Engine generates draft at click, Circle member reviews and confirms) implements the paper's principle that sponsorship *"validates the issue's priority and assigns accountability for resource usage"* — the sponsor actively commits to the proposal, they do not passively forward a thread.

---

## 6. W_h preliminary status and bootstrap self-verification

**Paper:** Describes bootstrapping at a process level — establish founding principles, identify seed Circles, establish initial competence baselines. Does not specify how the vSTF pool can form before verified competences exist, or how to handle credential claims before peer review has happened.

**Orb Sys:** Introduces `wh_preliminary` as a transient status for unverified claims. Preliminary values are used solely to seed the vSTF candidate pool — they carry no governance weight and cannot influence votes until verified. The vSTF pool verifies itself: members with preliminary W_h in a Dormain review each other's claims for that Dormain, blind and parallel, under the same process used for all future vSTF work.

**Why:** This solves the bootstrapping paradox — you need competence weights to form a vSTF, but you need a vSTF to establish competence weights — without creating a special "setup mode" that bypasses governance. The self-verification approach is the same peer review logic the system uses in perpetuity; there is no distinction in the ledger between a founding member's W_h record and a post-bootstrap member's. The paper is explicit that the bootstrap should use the system's native mechanisms from day one.

---

## 7. Post-bootstrap membership flow

**Paper:** States members join *"via invite or open application per Membership Circle policy"* but does not specify how applications are submitted, what information they carry, how the Membership Circle review works, or how the policy is governed.

**Orb Sys:** `membership_policy` is a `sys_bound` org parameter with three values (`open_application`, `invite_only`, `closed`), changeable only through the standard governance lifecycle. `POST /members/apply` creates a `MemberApplication` record; the Membership Circle reviews and approves via `POST /members/applications/:id/review`, which atomically creates the Member account.

**Why:** The paper's intent — that joining is governed by the community's Membership Circle, not by unilateral administrative action — requires a concrete mechanism. The policy-as-governed-parameter design ensures that changing who can join requires a governance motion, not a settings change by an administrator. This is a direct operationalisation of the paper's principle that all significant decisions pass through the autonomy-audit loop.

---

## 8. `bootstrapped_at` as the single bootstrap completion signal

**Paper:** Describes bootstrapping as a multi-step process culminating in the founding resolution, after which the founding Circle dissolves and normal operations begin. Does not specify how the system distinguishes between bootstrap and live states.

**Orb Sys:** `bootstrapped_at = null` means bootstrap is in progress; `bootstrapped_at = <timestamp>` means the org is live. `POST /org/bootstrap-complete` is the explicit transition endpoint. At transition: `POST /auth/register` begins returning 403, founding circles are dissolved, membership_policy is seeded, and a ledger event is written.

**Why:** A single boolean-equivalent field is the cleanest implementation of a state transition. The alternative — deriving live state from the presence of certain records — creates ambiguity and makes the system's behaviour dependent on whether those records were created in the right order. The paper's bootstrapping insight — that the system should use its own mechanisms from step one, with no suspended governance — is preserved: `bootstrapped_at = null` is not a suspended state, it is simply a state where `POST /auth/register` still works and circle invites auto-confirm.

---

## 9. Circle invitation: immediate acceptance in v1.0

**Paper:** The founding vacancy-filling process requires a vetting xSTF and a competence-based confirmation. Implies ongoing Circle membership changes follow a similar process.

**Orb Sys v1.0:** A Circle member inviting a new member creates the `CircleMember` row immediately. The inviting member must themselves be in the Circle — that is the v1.0 competence gate.

**Why:** The full Circle-vote confirmation mechanism (existing members vote on each invitation, a vetting xSTF reviews the candidate) is correct per the paper but requires a dedicated vote flow, notification cycle, and quorum check. In v1.0 this was deferred to v1.1 to avoid shipping a half-implemented feature. The current implementation documents the shortcut explicitly and the data model does not need to change to add it — a `circle_invitations` table and a vote step before `CircleMember` creation is the planned v1.1 path.

---

## 10. W_s decay floor

**Paper:** Describes decay as reflecting *"the perishable nature of skill relevance"* — if a member stops contributing, their effective influence decays. The paper does not specify whether decay reaches zero or floors at some minimum.

**Orb Sys:** `decay_floor_pct = 0.30` — W_s cannot decay below 30% of its peak value.

**Why:** Full decay to zero would mean a long-absent expert who returns to the community has zero governance weight until they rebuild from scratch. A floor preserves some residual recognition of past contribution while still applying decay pressure. The value 0.30 is a judgment call; it should be governed per-Dormain (some fields decay faster — a 2018 security certification is more stale than a 2018 philosophy credential) and the default can be overridden via the standard governance motion process.

---

## 11. Notification priority tiers

**Paper:** Mentions burnout guardrails — notification capping and STF rotation schedules — as Insight Engine functions. No priority levels or specific numbers are given.

**Orb Sys:** P1 (always delivered: STF deadlines <24h, vote closing <2h, judicial flags), P2 (capped: 12/day, 3/hour — invitations, sponsorships, slot offers), P3 (digest-only, v1.0 deferred — curiosity matches, health updates).

**Why:** The paper's concern is burnout from notification overload. The three-tier model is a standard notification design pattern that operationalises that concern — critical governance events are never dropped, routine updates are rate-limited, and low-priority signals are batched. The specific cap numbers (12/day, 3/hour) are reasonable defaults for a governance platform but should be tunable per org via parameters.

---

## 12. Cell composition profile and aSTF gap-filling

**Paper:** *"When a motion involves competence domains that are critically underrepresented in the Circle's membership, the random selection algorithm for the aSTF is biased to include members with high competence in those missing domains."* This is stated as a principle.

**Orb Sys:** Operationalised into a specific `CellCompositionProfile` object computed by the Integrity Engine from contribution records, stored in the ledger, and fed to the Inferential Engine's aSTF candidate scorer as a `composition_gap` weighting term. The profile is also queryable via `GET /cells/:id/composition-profile`.

**Why:** The paper's intent is that audits have the domain expertise to assess what was deliberated. Computing the profile from *actual contributions* (not just who was invited) is a meaningful refinement — it reflects who actually engaged, not just who was at the table. Making the profile queryable lets Circle members see the gap analysis before crystallising a motion, which can surface missing perspectives before Gate 1 rather than after.

---

## 13. Technology stack choices

**Paper:** Mentions Verifiable Digital Credentials (W3C) for W_h, a tamper-evident ledger (blockchain as one option), and Human-Centered AI principles for the engine layer.

**Orb Sys:** PostgreSQL 16 with append-only triggers and SHA-256 hash chain; NATS JetStream for event routing; FastAPI + SQLAlchemy for the API; Next.js 15 for the frontend; Anthropic Claude for Insight Engine LLM drafts.

**Why:** The paper is technology-agnostic by design. The choices here prioritise operational simplicity over the paper's blockchain suggestion — a PostgreSQL hash chain achieves tamper-evidence with far lower operational complexity than a distributed ledger, at the cost of requiring trust in the database operator rather than the consensus mechanism. For most PAAS deployments (organisations under a few thousand members), this is an acceptable trade-off. The paper explicitly lists a blockchain backend as a future research direction, and the architecture was designed so that the ledger layer can be swapped without changing the governance logic above it.

---

## What was not implemented

Two paper features are specified but absent from v1.0:

**Endorsement provenance weighting:** The paper describes a confidence tier on endorsements — high-confidence endorsements (with linked evidence and detailed rationale) carry more weight than low-confidence single-click endorsements. The `provenance_link` field exists in the schema, but the confidence multiplier in the ΔC formula is not yet computed. All endorsements are treated as equivalent weight by provenance level. This is a known gap.

**Cross-Dormain transfer coefficients:** The paper specifies that competence in a child Dormain should partially transfer to the parent (α = 0.6) and to related siblings (α = 0.2–0.4). Orb Sys treats Dormains independently. This means a member who builds W_s in "Cryptographic Protocols" does not automatically accumulate partial credit in "Security" even if the two Dormains are in a parent-child relationship. Transfer coefficients require a full Dormain hierarchy definition — the paper acknowledges this as dependent on the org's taxonomy — and are deferred to v1.1.


---

## 15. First-run bootstrap: template selector and founding circle formation

**Paper:** Describes a bootstrapping process where founding principles are established through community deliberation, seed Circles are identified, and initial competence baselines are set. Does not specify how an operator starts the system, how the founding circle is selected, or how initial governance proposals are surfaced.

**Orb Sys:** A first-run template selector (5 primary + 5 extended templates) lets the first operator choose a governance archetype. This seeds Dormains, parameter defaults, and a set of pre-drafted founding proposals — all authored and pre-sponsored by the system. The founding circle is not appointed by the operator.

**Founding circle formation:** When members register and submit W_h credentials, each vSTF that verifies a credential also evaluates founding circle fit. Any member with at least one verified credential is recommended for the founding circle. Once a threshold of recommended members is reached (min 3, target scales with org size estimate), the founding circle forms automatically from those verified members.

**Why:** The paper requires that the system uses its own native mechanisms from bootstrap day one. The vSTF that verifies credentials is already the competence verification mechanism — extending it to evaluate founding circle fit avoids inventing a separate selection process. The threshold-based auto-formation means no operator has unchecked power to appoint the founding circle. Members who verify credentials first have priority — this is chance, but it reflects demonstrated commitment (going through credential verification) rather than arbitrary appointment.

**Founding proposals:** Pre-drafted, pre-sponsored Cells open in sequence when the founding circle forms. They are questions, not decisions — "should this org's Commons be public or private?" not "set commons_visibility to public." The founding circle deliberates and files real motions. The bootstrap_complete Cell surfaces only when all mandatory proposals have enacted Resolutions, ensuring the founding circle cannot skip governance to rush past bootstrap.

**Template differentiation:** Templates vary primarily in parameter defaults and the founding proposal set — not in operations. Each template's proposals reflect the governance questions most relevant to that archetype. Dormains use general academic/professional categories to remain applicable before the founding circle renames them.


---

## 16. Platform-level identity (federation layer)

**Paper:** Treats each PAAS instance as a single-org deployment. Members are scoped to one organisation. Does not address multi-org participation or portable identity.

**Orb Sys:** Introduces a platform account layer above org membership. A `PlatformAccount` (handle, legal name, email, password) is created once. An org `Member` row is an org-scoped membership linked to a platform account. One person can hold multiple memberships across independent orgs under the same platform identity.

**Identity layers:**
- `legal_name` — platform-level, anchored, hard to change, optional verification reference
- `handle` — globally unique across the platform, used for invitations and notifications
- `display_name` — org-specific, can be anything including anonymous personas

**Credential wallet:** The platform account carries a document locker (`credential_wallet` table) — uploaded files and links representing claimed credentials. This is not verification state. Each org runs its own independent vSTF verification. Verified W_h records belong to the org. If an org deletes its data, the verified record goes with it. The wallet survives because it contains only the applicant's own documents.

**Why:** The org-slug-in-login pattern was a UX and architectural category error — it conflated the human with a specific org membership. Separating the two makes the system usable for people who participate in multiple communities, and makes the credential workflow sensible: you upload your PhD certificate once, then present it to each org for their own independent verification. Cross-org credential trust (org B accepting org A's vSTF verdict) is deferred to v2.

---

## 17. aSTF structured rubric (motion aSTF)

**Paper:** Specifies that the aSTF reviews decisions for "process soundness, evidence quality, ethical alignment, and conflicts of interest." Does not define a structured scoring instrument. The binary verdict (Approve/Reject) is the specified output, plus the revision_request extension in Orb Sys (see §1).

**Orb Sys:** Implements a four-dimension rubric that guides each reviewer toward their verdict:

| Dimension | Max | Measures |
|---|---|---|
| Jurisdiction | 9 | Does the Circle have mandate authority here? |
| Depth/Effort | 5 | Was deliberation substantive? |
| Alignment/Conflict | 10 | Does the decision advance org tenets? Undisclosed conflicts? |
| Competence | 6 | Were the right people in the deliberation? |
| **Total** | **30** | |

**Weighting rationale:** Alignment/Conflict (10) is the heaviest because it is the core PAAS legitimacy check — a Circle acting within mandate but advancing faction interests is a more serious failure than a Circle with thin deliberation (Depth, 5). Jurisdiction (9) is heavy because out-of-mandate action is structural, not correctable by more effort. Competence (6) is lighter because composition gaps can be addressed through the Inferential Engine's gap-filling without necessarily invalidating the decision.

**The rubric guides, it does not decide.** Reviewers see a running total as they score, but the verdict (Approve/Revision Request/Reject) is explicitly filed as a separate judgment. The scores are the published evidence; the verdict is the human determination. Mechanising the verdict from the score would undermine the purpose of independent human audit.

**Malpractice flagging:** Motion aSTF reviewers can flag specific deliberation participants for jSTF pre-referral alongside any verdict — even an Approve verdict. The motion can be sound while a participant's behaviour was not. The flag creates a `jstf_pre_referral` ledger event; the Judicial Circle decides whether to commission a full investigation.

---

## 18. Periodic aSTF (p-aSTF) — Circle health review

**Paper:** Describes periodic Circle health audits as a continuous oversight mechanism. States that the aSTF "regularly audits Circle performance." Does not specify the review structure, how members are individually assessed, or how the reviewing body is composed.

**Orb Sys:** Implements a two-layer periodic review with a distinct rubric for each layer.

### Layer 1 — Circle rubric (all reviewers, 30 pts)

Based entirely on publicly observable information — the Circle profile page, Commons activity, motion and resolution record. No access to internal deliberations required. Any engaged org member could answer these questions.

| Dimension | Max | Measures |
|---|---|---|
| Activity | 6 | Is the Circle visibly active in governance? |
| Competence Fit | 7 | Does actual member W_s match mandate Dormains? |
| Discipline | 6 | Does it stay within its mandate? |
| Cohesion | 5 | Does it act as a collective or as isolated individuals? |
| Delivery | 6 | Does it follow through — enacted resolutions, Gate 2 pass rate? |
| **Total** | **30** | |

The Competence Fit dimension is pre-computed by the Inferential Engine (percentage of mandate Dormains with W_s ≥ 800 among Circle members) and surfaced as a data point on the reviewer's screen. The reviewer translates the number into a score — the data informs but does not replace the judgment.

### Layer 2 — Member rubric (assigned reviewers only, 35 pts health + 2 risk flags)

Filed only for the reviewer's assigned members (1–3 per reviewer). Reviewers have access to the assigned members' public governance records and — uniquely — their deliberation contributions within the Circle.

| Dimension | Max | Measures |
|---|---|---|
| Effectiveness | 5 | Responsive to matters that concern the Circle |
| Stewardship | 7 | Projects the org's vision in their work |
| Participation | 5 | Present and active |
| Investment | 8 | Genuine skin in the game vs. seat-filling |
| Productivity | 6 | Adds unique value |
| Role Fit | 4 | Understands what the Circle requires of them |
| **Health subtotal** | **35** | |

Investment (8) is the heaviest dimension — the strongest single predictor of governance quality. Stewardship (7) is second because carrying the org's vision is the central PAAS accountability principle. Role Fit (4) is lightest because role understanding can develop; it is not grounds for serious concern on its own.

**Risk flags** (separate from health score, not additive):

- **Replaceability** (0–5): Would the org lose its way if this member were removed? Score > 3 triggers a knowledge-transfer mandate — a structural risk signal, not a quality judgment.
- **Indispensable** (0–5): Would the org move closer to its vision if this member were removed? Score > 3 triggers a jSTF pre-referral consideration — the anti-capture signal.

### Bipartite reviewer assignment

The p-aSTF pool is assembled using the same independence-weighted candidate scoring as the motion aSTF. Each reviewer is assigned 1–3 Circle members (never all of them). Each member receives assessments from 2–3 independent reviewers. The reviewer sees only their assigned members' data — not the full Circle roster, not other reviewers' scores.

This design limits each reviewer's exposure to the Circle's internal affairs while ensuring sufficient independent coverage per member. It reflects the PAAS principle of maximum participation: many reviewers each doing a bounded task rather than a small set of reviewers doing exhaustive work.

### Health tier

Each reviewer files one of three health tiers (Healthy/Watch/Concern) alongside their rubric. The Integrity Engine majority-votes the final tier. The tier is the reviewer's judgment; the rubric scores are the published evidence.

### Reviewer availability

Members can declare standing availability for review work. This is distinct from Curiosity (topical interest) — it is availability for the audit role specifically. The Inferential Engine uses it to build review pools on demand. Reviews happen continuously on each Circle's individual schedule (anchored to founding date, event-triggered on anomaly flags). No global audit calendar — no term-based politics.

### What all p-aSTF records go to the ledger

All scores, verdicts, and health tiers are published to the open ledger after the review completes. Reviewer attribution is permanently sealed — who scored whom is never disclosed. Every org member can see the aggregate scores for every Circle and every member. The transparency is maximal; the retaliation surface is eliminated.

---

## 19. The unit of assessment in p-aSTF is the individual member; the aggregate is the Circle

**Paper:** Discusses Circle health as a whole-Circle property. Does not specify whether the reviewing mechanism assesses members individually or the Circle collectively.

**Orb Sys:** The unit of assessment is the **individual member**. A p-aSTF reviewing a Circle with 7 members produces 7 member rubric assessments (each from 2–3 reviewers) plus one circle rubric assessment (from all reviewers). The Circle health score is derived from the aggregate of member-level assessments plus the Circle-level assessment — not the reverse. This means a Circle with one member pulling the entire score down is distinguishable from a uniformly mediocre Circle, even at the same mean.

**Why:** The paper emphasises that PAAS replaces positional authority with individual demonstrated competence. A Circle health score that doesn't trace to individual members makes accountability diffuse — the assessment should be as specific as the system's competence model, which is always individual and domain-specific. The aggregate health score exists for convenience; the member-level breakdown is the substantive finding.
