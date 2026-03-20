# Orb Sys
## Implementation Draft — v7
*A PAAS Installation Specification*

> Orb Sys is a software product that installs the Polycentric Autonomy-Audit System (PAAS).
> This document defines the screens, flows, and logic of the Orb Sys platform — not the PAAS framework itself.
>
> **v7 changes:** §20 Motion Taxonomy & Structured Specification. All sections revised for markdown. System Custodian Circle replaces Systems Integrity Circle throughout.

---

## Table of Contents

1. [Personal](#1-personal)
2. [Deliberation](#2-deliberation)
3. [Org](#3-org)
4. [Cells](#4-cells)
5. [Circles](#5-circles)
6. [STF Dash](#6-stf-dash)
7. [Setup — Creating an Org](#7-setup--creating-an-org)
8. [Joining](#8-joining)
9. [Motions & Resolutions](#9-motions--resolutions)
10. [Circles — Architecture](#10-circles--architecture)
11. [Judicial Track](#11-judicial-track)
12. [Competence Management](#12-competence-management)
13. [AI Layer](#13-ai-layer)
14. [Org Parameters](#14-org-parameters)
15. [Evaluation Philosophy](#15-evaluation-philosophy)
16. [Member States & Circle Health](#16-member-states--circle-health)
17. [Cell Architecture & Workspace Protocol](#17-cell-architecture--workspace-protocol)
18. [Commons Protocol](#18-commons-protocol)
19. [Proposal & Permission Architecture](#19-proposal--permission-architecture)
20. [Motion Taxonomy & Structured Specification](#20-motion-taxonomy--structured-specification)

---

## 1. Personal

Profile data, Dormain Metrics (Competence vs Curiosity per Dormain), Cells history, Circles membership CV.

**Dormain Metrics:** dual-axis per Dormain showing `W_h + W_s` against Curiosity signal. Gap between the two is informative and not required to close. A member can be high-competence in Economics and high-Curiosity in Governance simultaneously — the system surfaces both.

---

## 2. Deliberation

Active governance workspace for a member.

- **Timeline / Feed** — activity across Cells and Circles the member belongs to
- **STF Dash** — all active STF instances the member is currently assigned to
- **Inbox** — notifications, Insight Engine nudges, scheduling alerts, burnout guardrail warnings

---

## 3. Org

Organisation-level view. Readable by all members; write access governed by Circle membership and the proposal lifecycle.

- Profile data — name, purpose, founding tenets
- **Dormain Metrics** — composition competences (aggregate of what all members hold) vs desired competences (target ratios), per mandated Dormain
- Circles — full list with info and members
- Motions — all active motions across the org
- Resolutions — passed resolutions with full status trail
- Files
- **Audit Archive** — aSTF reports, Integrity Engine logs, vSTF audit records, Judicial rulings. Immutable and publicly readable within the org.

---

## 4. Cells

Contextual workspaces. See [§17](#17-cell-architecture--workspace-protocol) for full architecture.

---

## 5. Circles

- Profile data including tenets and mandated Dormains
- **Dormain Metrics** — member composition competences vs Circle's mandated Dormain targets
- Members — current roster with active states; historical membership with full exit state record
- **Circle Health** — rolling view across recent periodic aSTF cycles
- Motions — active and historical
- Resolutions — with full status trail
- STF Reports — aSTF verdicts associated with this Circle's decisions

---

## 6. STF Dash

Per STF instance view. All STF types share this interface structure; each type has distinct configuration and visual treatment.

| Field | Description |
|---|---|
| Type | xSTF / aSTF / vSTF / jSTF / Meta-aSTF |
| Mandate | Purpose and scope |
| Dormain(s) | Domain tags |
| Deadline | Filing deadline |
| Report | Filed report (when complete) |
| Verdict | Approve / Reject / Deviation Flagged / Contested |
| Attachments | Supporting evidence |
| Associated Circle(s) | Which Circles this STF serves |
| Access flag | aSTF, vSTF, jSTF marked write-restricted (independence preserved) |

---

## 7. Setup — Creating an Org

Setup is a bootstrapping sequence, not a configuration form. Order matters.

1. Create Org — profile, purpose, founding tenets
2. Define mandated Dormains and desired competence ratios
3. Set Commons visibility policy (`members-only` | `public` | `per-dormain`)
4. Instantiate starting Circles — the system suggests named Circles with pre-filled mandates and Dormains to reduce bootstrap confusion. Founders may accept, modify, rename, or replace any of them. No Circle is created with elevated system permissions. All Circles are the same object with different configured mandates.
5. Invite founding members

### Suggested Starting Circles

> These are suggestions. A new Governance Circle may be created. A Membership Circle 2 may be added for volume. Any Circle may be renamed. The names carry no system-level meaning. The Integrity Engine knows mandates and Dormains, not Circle names.

| Circle | Suggested Mandate |
|---|---|
| Governance Circle | Constitutional parameters: Dormain definitions, desired ratios, voting thresholds, org-level settings |
| System Custodian Circle | System integrity custodianship. First invited on system-related proposals by Dormain match. Does not hold write access — that is held exclusively by the Integrity Engine. |
| Org Integrity Circle | Competence verification, vSTF commissioning, W_h disputes, periodic audit scheduling, code of conduct |
| Membership Circle | Onboarding pipeline, membership status, Judicial track sanctions. May be duplicated for volume. |
| Judicial Circle | jSTF and Meta-aSTF commissioning, due process oversight. High W_h prerequisite. |
| Treasury Circle | Resource allocation, budget resolutions. Minimum W_h required. On by default. |

---

## 8. Joining

1. Create profile and declare competences and Curiosities
2. **W_h** — AI-assisted credential pre-check → vSTF forensic audit → aSTF approval (treated as high-stakes Motion)
3. **W_s** — starts at system baseline; updated continuously via ΔC formula through participation; periodically audited by vSTF
4. Begin deliberating in Commons and Cells → earn W_s → become eligible for Circle membership and STF roles
5. Inferential Engine prioritises high-Curiosity, lower-Competence members for novice-reserved STF slots

---

## 9. Motions & Resolutions

### 9a. Proposal Origins

**Commons-originated**
A Commons thread accumulates discussion. The Insight Engine generates a draft proposal from the thread content, attributed to the contributors whose arguments shaped it. A Circle member whose Circle has Dormain mandate over the thread sees a `Sponsor as Proposal` option and reviews the draft. If they sponsor it, the draft proposal becomes the Cell's founding mandate — the snapshot at sponsorship.

**System-action-originated**
A Circle member initiates a proposal from a system action directly (Edit Org Name, adjust a parameter, propose a new Circle, etc.). Any Circle member may initiate regardless of whether their Circle has mandate over the action. The Inferential Engine routes the proposal to the Circles that do have mandate. The initiating Circle is not required to have mandate.

> Ordinary members (non-Circle) may discuss freely in Commons but cannot sponsor or initiate proposals. Circle membership is the threshold for proposal initiation.

### 9b. Motion Lifecycle

```
Proposal initiated (Commons sponsorship or system action)
  → Deliberation Cell created
      Access set by sponsor: open or closed
      Writable only to invited participants regardless of visibility
  → Inferential Engine invites all Circles with mandate over proposal Dormain(s)
  → Cell deliberates; Insight Engine generates rolling minutes
  → Motion crystallised
      Insight Engine drafts motion from Cell record (see §20 for format by type)
      Cell temporarily closes
  → Motion Review Sub-Cell opened — Gate 1 aSTF (blind parallel)
      Gate 1 asks: was the deliberation sound and the decision legitimate?
  → Approved → Resolution created, status: Pending Implementation
  → Rejected  → Deliberation Cell reactivated with aSTF rationale attached
```

### 9c. Resolution Status Flow

```
Draft
  → Active (in deliberation)
  → Voted
  → Gate 1 aSTF: Approved  →  Pending Implementation
  → Implemented (by relevant actor)
  → Gate 2 review:
       → Enacted ✓  (Integrity Engine locks if Sys-bound)
       → Contested  → back to implementer (no re-vote on intent)
       → Deviation Flagged + Justified  → Enacted with audit note
       → Deviation Flagged (unjustified) → competence penalty / judicial escalation
```

### 9d. Implementation Types & Gate 2 Agents

| Resolution Type | Implements | Gate 2 Agent |
|---|---|---|
| System parameter change | Integrity Engine (automatic, on enacted Resolution) | aSTF — exact diff; hard lock |
| Org / Circle identity change | Integrity Engine (automatic) | aSTF — diffs against resolution text |
| Competence adjustment | Integrity Engine / Org Integrity Circle | vSTF |
| Disciplinary / sanctions | Membership Circle | jSTF |
| Org-bound / physical | Responsible Circle (self-declared) | aSTF — audit only, no rollback possible |

> For org-bound resolutions the system has no hands. Human agency is preserved throughout.

---

## 10. Circles — Architecture

All Circles are the same object with different configured mandates and Dormains. No Circle holds elevated permissions over any other. A Circle's influence in any deliberation is determined entirely by whether its Dormain matches the proposal's Dormain tag.

### 10a. Suggested Starting Circles

See [§7](#7-setup--creating-an-org) for the full table.

### 10b. Optional Circles

| Circle | Suggested Mandate |
|---|---|
| Knowledge & Archive Circle | Institutional memory: resolution precedent, STF report canon, knowledge base |
| Standards & Ethics Circle | Code of conduct and tenet definitions. Distinct from Judicial. |
| External Relations Circle | Outside interfaces: partners, regulators, press |
| Development Circle | Growth: onboarding design, novice mentorship, competence pathways |

> Setup prompt: *"These are suggested starting Circles. Accept, rename, or replace them. You can add more Circles now or at any time via the standard motion process."*

---

## 11. Judicial Track

**Triggered by:**
- Integrity Engine anomaly flag (unusual voting patterns, auditor-auditee correlation, Sybil-like activity)
- Competence-gated formal complaint meeting threshold
- Repeated defiant resubmission of a rejected Motion

**Process:**
1. Judicial Circle commissions a Judicial xSTF — neutral members, high W_h in forensics, ethics, and relevant Dormain; no prior involvement in the case
2. Judicial xSTF investigates → produces Investigation Report (findings, evidence, points of concern, recommended course of action)
3. Meta-aSTF audits the investigation itself (not the original case) → Final binding ruling
4. Anonymisation available for arbiters where intimidation risk is assessed
5. Integrity Engine may freeze the accused member's Competence Multiplier (`M_cmp`) during investigation

**Sanctions (Meta-aSTF exclusive mandate):**
- Competence deduction
- Temporary suspension — reinstatement date shown on member record
- Circle flush and re-vetting
- Org expulsion

> All steps immutably logged. Vacancies trigger the standard vetting pipeline: Inferential Engine prepares candidate list, vetting xSTF reviews, highest-endorsed candidate fills the role.

---

## 12. Competence Management

- **W_h submission** → AI credential pre-check → xSTF forensic audit → aSTF approval
- **W_s** updated continuously via ΔC formula; periodically audited by vSTF on rotation schedule
- Integrity Engine flags anomalies: sudden score spikes, statistical correlation between auditor and audited body
- Competence Multiplier (`M_cmp`) may be frozen during active judicial investigation
- Dormain Metrics on Personal, Circle, and Org profiles all derive from the same Competence data at different aggregation scopes

---

## 13. AI Layer

> All three engines are non-directive. No engine may initiate a Motion, cast a vote, or impose a sanction. Matching and recommendation logic is visible to the member it affects.

| Engine | Function |
|---|---|
| **Inferential Engine** | Matches members to Cells and STF roles via Competence + Curiosity vectors. Tags Commons and Cell content by Dormain. Routes proposals to Circles with mandate. Auto-scales xSTF slots when pending volume exceeds threshold. Prioritises high-Curiosity, lower-Competence members for novice slots. Controls visibility of `Sponsor as Proposal` by Dormain match. |
| **Insight Engine** | Generates draft proposals from Commons thread content (attributed). Produces rolling Cell minutes. Scheduling, notifications, discussion summarisation, fact-checking. Burnout guardrails: notification caps, STF rotation window limits. Cites active motions and resolutions against Commons threads. |
| **Integrity Engine** | Tamper-evident ledger of all governance actions. **Holds exclusive system write access — applies changes only on enacted Resolutions.** Anomaly detection and alerting. Competence Multiplier management. Gate 2 diff engine. Aggregates periodic aSTF findings into Circle Health scores. Enforces blind review isolation in aSTF / vSTF sub-Cells at the data layer, not only UI layer. |

---

## 14. Org Parameters

Managed via the standard proposal lifecycle — any Circle member may initiate a parameter change; Circles with mandate deliberate; aSTF gates; Integrity Engine applies on enactment.

| Parameter | Default |
|---|---|
| Activity Gravity values | Per contribution type (post G=0.5, motion G=1.0, audit G=1.2) |
| STF rotation window | 2–12 weeks |
| Dormain alignment target ratios | Set at founding |
| xSTF auto-scaling threshold | Configurable |
| Novice slot reservation floor | 30% |
| Voting threshold per Circle type | Majority / supermajority per Circle config |
| Gate 2 waiver threshold | Minimum change magnitude; not applicable to disciplinary or competence changes |
| Commons visibility policy | `members-only` \| `public` \| `per-dormain` |

---

## 15. Evaluation Philosophy

> **The evaluation layer of Orb Sys is built on a single foundational principle:
> human judgment is the output, not the input to a formula.**

The aSTF is closer to a jury than a process auditor. A checklist exists, but no formula governs how it is weighted. Two panels reviewing the same Circle may reach different conclusions. That is not a flaw — it is the system normalising to the organisation's real human context.

The only consistent way to score well across a randomly composed, rotating panel of peers is to actually do the work well. You cannot optimise for a jury you have never met.

### 15a. Evaluation Modes by STF Type

| STF Type | Evaluative Question | Output |
|---|---|---|
| Motion aSTF | Was this decision sound and legitimate? | Approve or Reject + rationale. Not a mandate check — routing handled that. |
| jSTF | What actually happened and who bears accountability? | Investigation report: findings, evidence, points of concern, recommended course of action. |
| vSTF | Do these credentials hold up? | Adjusted W_h value + supporting rationale. |
| Periodic aSTF | Is this Circle genuinely fulfilling its mandate? | Multi-dimensional checklist, independently marked per reviewer. Integrity Engine aggregates. Score is residue of collective judgment. |

### 15b. How Scores Are Used

- Periodic aSTF score enters the Integrity Engine as a logged finding
- Informs future panels as context — like a judge reading prior rulings, not as a constraint
- Feeds Circle Health and Org Dormain Metrics
- Guides Inferential Engine routing decisions
- Contributes to individual W_s indirectly: as a signal about the quality of the governance environment, not as a direct calculation on any individual

> **What is never done:** no engine computes an evaluation. No formula produces a verdict. The Integrity Engine stores, aggregates, and surfaces — it does not judge. The moment evaluation becomes mechanical, the system produces compliance theatre, not governance.

---

## 16. Member States & Circle Health

### 16a. Active Member States

| State | Description |
|---|---|
| **Probationary** | Newly admitted. `M_cmp` may be reduced until first periodic aSTF cycle confirms fit. |
| **Active** | Full voting weight, normal participation. Default state. |
| **On Leave** | Voluntary temporary absence agreed with Circle. No voting weight during period. Slot held. |
| **Inactive** | Participation below threshold flagged by Insight Engine. Warning state. No formal action yet. |
| **Under Review** | Integrity Engine flag triggered. `M_cmp` frozen. Voting weight suspended. |
| **Suspended** | Judicial penalty imposed. Temporary. Reinstatement date shown if applicable. |

### 16b. Exit States

**Voluntary**

| State | Description |
|---|---|
| Resigned | Formal voluntary exit. Clean record. |
| Forfeiture | Abandoned duties without formal process. Carries a mark. |

**Competence-driven**

| State | Description |
|---|---|
| Competence Drift | W_s fell below Circle entry threshold. No stigma. Member may re-qualify and re-enter. |
| Credential Lapse | W_h credential expired or externally revoked. No stigma unless tied to misrepresentation. |

**Process-driven**

| State | Description |
|---|---|
| Rotation End | Normal STF term conclusion. Entirely positive exit. |
| Audit-Initiated Removal | Periodic aSTF findings triggered overseeing Circle action. Shown with linked aSTF report. |
| Transfer | Moved to another Circle. Positive exit. Destination Circle shown. |

**Structural**

| State | Description |
|---|---|
| Circle Reshuffle | Composition changed by Resolution. Member did not fail; structure changed. |
| Circle Dissolution | Circle ceased to exist. Linked to dissolution Resolution. |

**Disciplinary**

| State | Description |
|---|---|
| Judicial Penalty | Specific sanction. Linked to ruling. Permanent record. |
| Org Expulsion | Terminal. Linked to Meta-aSTF ruling. Highest severity. |

> The history view groups exits by category. A competence drift exit and a judicial penalty exit must not sit undifferentiated in the same list.

### 16c. Circle Health

Three dimensions tracked as a trend profile, not a single number:

| Dimension | What it measures |
|---|---|
| **Mandate Adherence** | Is the Circle doing what it was constituted to do? Periodic aSTF panels mark concerns against stated mandate and tenets. |
| **Activity** | Is the Circle actually deliberating? Dormant Circles holding formal status flagged via Insight Engine participation logs. |
| **Decision Quality** | Gate 1 aSTF approval rate on this Circle's motions over time. Declining rate is a leading indicator of process degradation. |

Circle Health is surfaced on the Circle profile as a trend across the last N periodic aSTF cycles, with the most recent cycle's areas of concern visible. It is not hidden from prospective members.

### 16d. Org Health

Composition of Circle Health scores weighted by each Circle's criticality to the Org's mandated Dormains. Weighting is determined by the Dormain alignment ratios set at founding by the relevant governance Circles.

A low-health Treasury Circle in a financially-mandated org is a more severe signal than a low-health optional Circle. Org Health is genuinely organisation-specific.

### 16e. Circle Performance & W_s

The pathway is indirect by design. The `M_cmp` multiplier does the primary work — Circle members have `M > 1`, so a well-functioning Circle naturally produces stronger W_s growth through richer participation signals. Periodic aSTF findings add contextual weight to nomination recommendations without mechanising individual scores.

---

## 17. Cell Architecture & Workspace Protocol

> A Cell is not a chat room. It is a contextual workspace whose configuration, access rules, input streams, and lifecycle are determined by what it is hosting.
>
> **The Cell is the room. The room changes shape depending on its mandate.**
> A Council Room for Circles. A Boardroom for xSTFs. A Blind Chamber for aSTF review. A Court for jSTFs.
> The architecture is the same. The configuration is not.

### 17a. Cell Types

| Cell Type | Configuration & Purpose |
|---|---|
| **Deliberation Cell** | Born from Commons thread sponsorship or direct Circle initiation. Access set by sponsor at creation (open or closed); writable only to invited participants regardless of visibility. Linked to Commons thread by snapshot reference. Insight Engine generates rolling minutes. |
| **Closed Circle Cell** | Restricted to invited Circles. Operationally private. Auditable by periodic aSTF and jSTF on mandate. Members know the Cell is closed but not dark. |
| **Motion Review Sub-Cell** | Spawned when a motion is filed. Hosts Gate 1 aSTF. Blind parallel: each reviewer isolated, sees same content, cannot see other reviewers. Integrity Engine enforces isolation at data layer. |
| **STF Cell** | Created for every STF instance. Configuration varies by STF type. See [§17c](#17c-stf-cell-configurations). |
| **Periodic Audit Cell** | Hosts periodic aSTF review. Semi-open: prior aSTF findings visible as context; current assessments isolated until all filed. |

### 17b. Cell State Model

```
Active
  → [motion crystallised]        → Temporarily Closed
       → [Gate 1 Approved]        → Archived (read-only)
       → [Gate 1 Rejected]        → Reactivated (aSTF rationale attached)

Active
  → [abandoned, no motion]       → Dissolved  (no archive entry — normal)
  → [frozen by Circle moderator] → Frozen     (governance exception, noted in archive)
  → [judicial flag]              → Suspended  (frozen, readable by jSTF only)

Archived → read-only. Commons thread remains live. Resolution cited by Insight Engine.
```

> Abandoned Cells are dissolved without entering the audit archive. Not every sponsored thread needs to become a motion.

### 17c. STF Cell Configurations

| STF Type | Cell Configuration | Key Constraint |
|---|---|---|
| **xSTF** | Collaborative. All members see each other. Working Cell. Produces report for sponsoring Circle. | Standard deliberation. Members known to each other. |
| **aSTF (motion)** | Blind parallel. Each reviewer isolated. Same content visible. No cross-communication. | Reviewer identities withheld until all verdicts filed. Integrity Engine enforces at data layer. |
| **aSTF (periodic)** | Semi-open. Prior aSTF findings visible as context. Current assessments isolated. | No live cross-reviewer visibility. Aggregation post-filing only. |
| **vSTF** | Blind parallel. Independent credential assessment per reviewer. | Identities withheld until all W_h assessments filed. |
| **jSTF (investigation)** | Collaborative within investigation team. Isolated from Meta-aSTF layer. | jSTF produces report. Meta-aSTF receives as read-only. No cross-layer communication. |
| **Meta-aSTF** | Receives jSTF report as read-only. Deliberates internally. Issues binding ruling. | Cannot re-investigate. Reviews due process, evidence sufficiency, proportionality only. |

### 17d. The Commons-to-Cell Link

When a Circle member sponsors a Commons thread, the Cell stores a reference to the Commons thread at the point of sponsorship — a snapshot link, not a live feed. The Insight Engine-generated draft proposal derived from the thread becomes the Cell's founding mandate.

Cell members access the Commons thread as ordinary org members by navigating to it themselves. The Insight Engine does not monitor the thread for drift and pipe updates into the Cell. That judgment call belongs to the humans.

If a Cell member notices a significant context shift in the Commons thread, they bring it into the Cell explicitly as a contribution, attributed to them. This is a governance act — they are choosing what is relevant.

> If a Cell member misses a significant Commons development and the motion proceeds on stale context, that is a human accountability issue — the kind a periodic aSTF would flag. The system did not fail. Someone was not paying attention. That distinction matters for how responsibility is assigned.

### 17e. Cell Visibility & Access Rules

| Cell Type | Read during activity | Read after archiving |
|---|---|---|
| Deliberation Cell (open) | Invited Circle members write; all org members read | All org members (read-only) |
| Deliberation Cell (closed) | Invited Circle members only | All org members (read-only) |
| Closed Circle Cell | Invited Circle members only | Periodic aSTF and jSTF on mandate only. Org archive holds aSTF report, not raw Cell record. |
| Motion Review Sub-Cell | Each reviewer sees own isolated view | All org members post-verdict (reviewer identities revealed after all verdicts filed) |
| STF Cell (xSTF) | STF members only | Sponsoring Circle + audit oversight |
| Periodic Audit Cell | Reviewers only (isolated per §17c) | Org archive receives assessment report, not raw Cell record |

### 17f. Commons Thread Moderation

Thread freezing is a moderation action on the Commons thread, not a Cell lifecycle state.

| Freeze type | Authority |
|---|---|
| **Conduct-based** | Membership Circle — for spam, harassment, policy breach. Logged in audit archive. |
| **Judicial** | Judicial Circle — ordered as part of a jSTF investigation. Thread read-only pending outcome. |
| **Policy-based** | Any Circle with governance mandate over the relevant Dormain — via standard motion process. |

> Freezing is noted as a governance exception in the audit archive. It is possible but not considered good governance practice. Rare, justified, and auditable.

---

## 18. Commons Protocol

The Commons is the org's open discussion space. No votes, no motions, no formal roles apply within it. It is where ideas exist before they have a home, and where they continue living after they have been acted on. It is a permanent record of the org's intellectual life.

### 18a. Structure & Visibility

- Commons is org-wide. One Commons per org installation.
- Visibility is a Governance Circle parameter: `members-only`, `public`, or `per-dormain`
- Public Commons may allow non-member contributions (read and post). Non-members cannot sponsor, vote, or access Cells.
- Per-Dormain visibility: granular control via Governance Circle Resolution

### 18b. Inferential Engine Role in Commons

The Inferential Engine is the **filter**, not the gatekeeper. Members browse freely. Its role is targeted:

- Circle members are surfaced threads whose Dormain tag matches their Circle's mandate — the 2 or 3 threads relevant to their mandate, not the full feed
- Members also see threads matching their personally declared Curiosities
- Everything else is accessible but not pushed
- Threads are tagged by Dormain automatically as content is posted. Circle members may manually correct a misclassification.

### 18c. Sponsorship Rules

1. Any Circle member whose Circle has Dormain mandate over a thread sees the `Sponsor as Proposal` option. Ordinary members do not see it.
2. Sponsoring creates a Deliberation Cell. Sponsor sets access (open or closed) at creation.
3. A thread can only be sponsored once. The thread displays an indicator: *active Deliberation Cell in progress*.
4. Duplicate threads on the same topic: Insight Engine surfaces prior art. Circle members bring new context into the existing Cell as explicit contributions.
5. The Insight Engine generates a draft proposal from the thread content, attributed to contributing members, for the sponsor to review before confirming. This draft becomes the Cell's founding mandate.

### 18d. Commons & Resolution Continuity

- Threads remain open after a Resolution is enacted from them
- Insight Engine cites the Resolution against the thread — members see what was decided and when
- Post-resolution discussion may generate new motions
- Thread accumulates history: original discussion → sponsorship → Resolution citation → post-resolution discussion

> The thread outlives the motion. Resolutions are outcomes of threads, not replacements for them.

---

## 19. Proposal & Permission Architecture

> **Core principle: no Circle holds elevated system permissions.**
> The Integrity Engine holds the keys.
> It applies system changes only on the basis of valid enacted Resolutions.
> A Circle's influence in any deliberation is determined by mandate and Dormain, not by system role.

### 19a. Who Can Propose

| Actor | Proposal Capability |
|---|---|
| Ordinary member | Discuss in Commons. Cannot sponsor. Cannot initiate system-action proposals. |
| Circle member | Sponsor Commons threads where their Circle has Dormain mandate. Initiate system-action proposals on any system action regardless of their Circle's mandate over the specific action. |
| Circle member (no mandate on action) | May still initiate. Cannot participate in the deliberation (Circle not invited). Risks accountability penalty if bad-faith. aSTF assesses quality, not proposer identity. |

### 19b. How Routing Works

1. Proposal is tagged with one or more Dormains by the Inferential Engine
2. All Circles whose configured mandate includes those Dormains are invited to the Deliberation Cell
3. The proposing Circle is included in the Cell regardless of mandate match — they initiated the proposal and are part of the record
4. Routing logic is visible: the Cell shows which Circles were invited and on what Dormain basis

> *Example:* A Culinary Circle member proposes changing the org name. Tagged as Governance + Brand. Governance Circle and Brand Circle invited. Culinary Circle present as initiator. The deliberation quality is determined by who showed up with relevant competence, not by who proposed it.

### 19c. The aSTF's Role in Proposals

Gate 1 aSTF does **not** check whether the proposing Circle had mandate. Routing already handled that. It asks:

- Was the deliberation process sound?
- Was the evidence adequate?
- Was participation sufficiently broad across relevant competences?
- Is the decision consistent with the org's tenets and mandate?

### 19d. System Write Access Model

| Actor | System Write Access |
|---|---|
| Any Circle (incl. System Custodian) | **None.** Circles deliberate and vote. They do not touch system parameters directly. |
| **Integrity Engine** | **Exclusive.** Applies parameter changes, Circle creations, membership changes, and all Sys-bound actions — only on a valid enacted Resolution with completed Gate 2 aSTF review. |
| System Custodian Circle | First invited on system-related proposals by Dormain match. Brings expertise to deliberation. Does not implement. If flushed: system integrity unaffected, expert voice reduced until reconstitution. |

**On the flush scenarios:**

```
System Custodian Circle flushed:
  Integrity Engine unaffected.
  Expert voice reduced in system deliberations until reconstitution.
  No system access is lost or gained by any other Circle.

Governance Circle has one member:
  Proposals still proceed.
  Thin deliberation is a process weakness the aSTF will flag.
  Audit trail is present. Bad faith has consequences.

Budget Circle proposes Governance threshold change:
  Tagged Governance Dormain.
  Governance Circle invited to deliberate.
  If vote fails → Cell dissolved.
  If it passes → aSTF assesses participation breadth.
  The system does not prevent the proposal. The process tests it.
```

### 19e. Circle Creation & Dissolution

- Creating a new Circle is a Sys-bound action — full proposal lifecycle. Any Circle member may initiate.
- Dissolving a Circle is the same process.
- Dissolving foundational Circles (those with broad governance mandate overlap) will naturally require broader deliberation because the Inferential Engine will invite more Circles with mandate — not because of a hard technical lock.

> There is no hard technical lock preventing any Circle from being dissolved. The protection is the deliberation process, the aSTF, and the audit trail — not a permissions wall. A system that can't be changed is as dangerous as one that can be changed too easily.

---

## 20. Motion Taxonomy & Structured Specification

A motion is not always a text statement. The format of a motion is determined by what is being decided. Two base types, one hybrid form.

> The motion type is determined at proposal initiation, not at filing. A system-bound proposal cannot drift into a text motion mid-deliberation. The Cell knows what it is producing from the moment it opens.

---

### 20a. System-Bound Motion — Specification Format

The output of a system-bound deliberation is a **machine-parseable change specification**. The motion *is* the implementation instruction. The Integrity Engine reads it and applies it. There is no interpretation step.

```
MOTION TYPE : system-bound
MOTION ID   : [auto-assigned]
CIRCLE(S)   : [deliberating Circles]
DATE        : [crystallisation date]

SPECIFICATION:
parameter              : new_value              : justification
novice_slot_floor      : 0.40                   : increase participation pipeline per Cell #18 findings
rotation_window_weeks  : 3–10                   : reduce burnout risk, Insight Engine flag Q3
voting_threshold_super : 0.65                   : align with amended tenet §4

DELIBERATION RECORD:
weighted vote — relevant Dormains: YEA 847 / NAY 312
participating Circles            : [list]
Insight Engine minutes ref       : [Cell ID]

GATE 1 aSTF  : [pending / approved / rejected]
GATE 2 CHECK : diff(applied, specification) — exact match required
```

**Gate 2 for system-bound motions is a diff, not an audit.** Either the Integrity Engine applied `novice_slot_floor = 0.40` or it did not. There is no ambiguity zone. A failed diff returns the motion to Contested status; there is no "justified deviation" category for system-bound changes.

**Pre-filing validation:** The Integrity Engine validates the specification before Gate 1 opens — out-of-range values, non-existent parameter names, missing justifications. A malformed system-bound motion is returned to the Cell for correction without consuming an aSTF.

---

### 20b. Non-System Motion — Directive Format

The output is a **text directive**. Short or long. It expresses intent, policy, or decision in natural language. It cannot be machine-applied because what it is changing is in the world, not in the system.

```
MOTION TYPE : non-system
MOTION ID   : [auto-assigned]
CIRCLE(S)   : [deliberating Circles]
DATE        : [crystallisation date]

DIRECTIVE:
The Meridian Collective will commission an independent external review of its
research output methodology every two years, beginning Q1 2025. The review
panel shall include no fewer than two members with active W_h credentials in
Research Methods. Findings shall be published to the public Commons within
30 days of completion.

DELIBERATION RECORD:
weighted vote — relevant Dormains: YEA 1204 / NAY 88
participating Circles            : [list]
Insight Engine minutes ref       : [Cell ID]

GATE 1 aSTF  : [pending / approved / rejected]
GATE 2 AUDIT : interpretive — did what happened align with the spirit and
               letter of this directive?
               Deviation spectrum: justified / unjustified / partial with explanation
```

**Gate 2 for non-system motions is judgment work.** The aSTF assesses compliance on a spectrum. Justified deviation (the external reviewer panel was constituted slightly differently due to credential availability, documented) is noted with an audit note and enacted. Unjustified deviation (the review simply wasn't commissioned) is flagged and escalates.

---

### 20c. Hybrid Motion — Specification + Directive

Some decisions have both a policy intent and a set of parameter changes that implement it. The hybrid form carries both.

```
MOTION TYPE : hybrid
MOTION ID   : [auto-assigned]
CIRCLE(S)   : [deliberating Circles]
DATE        : [crystallisation date]

POLICY DIRECTIVE:
In order to encourage novice participation and reduce competence concentration
in high-stakes deliberations, the following parameters are updated and the
Development Circle is accountable for reporting on outcomes.

SPECIFICATION:
parameter              : new_value : justification
novice_slot_floor      : 0.40      : increase from 0.30 per Development Circle analysis
xstf_scaling_threshold : 12        : lower threshold to open parallel slots sooner

POLICY ACCOUNTABILITY:
Development Circle to report novice participation rates at next periodic aSTF cycle.

DELIBERATION RECORD:
weighted vote — relevant Dormains: YEA 960 / NAY 201
participating Circles            : [list]
Insight Engine minutes ref       : [Cell ID]

GATE 1 aSTF  : [pending / approved / rejected]
GATE 2 CHECK :
  — specification block: diff(applied, specification) — exact match required
  — directive block: interpretive audit of policy accountability clause
  Both blocks assessed independently. Each can succeed or fail on its own.
```

---

### 20d. Insight Engine's Role in Motion Drafting

The Insight Engine drafts the motion from the Cell's deliberation record. The format it produces depends on the motion type:

| Motion Type | Insight Engine Output |
|---|---|
| System-bound | Extracts proposed parameter changes from deliberation, populates specification fields, generates justification text from discussion context, attributes contributions |
| Non-system | Synthesises deliberation into a directive statement, identifies key commitments made, flags ambiguities for Circle members to resolve before filing |
| Hybrid | Separates parameter changes from policy commitments, drafts both blocks, flags accountability clauses for explicit Circle member confirmation |

Circle members review the draft before the Cell closes. The draft is a starting point — Circle members may edit, reject, or request a redraft. The Insight Engine does not file the motion; a Circle member confirms and files.

---

### 20e. Weighted Vote Record

All motion types carry the same deliberation vote record, regardless of format:

```
weighted vote — relevant Dormains: YEA [score] / NAY [score]
```

The vote is not a head count. It is the sum of Competence-weighted votes (`W_s + W_h` with `M_cmp` applied) across all participating members in the relevant Dormains. A member with high competence in the Dormain being decided carries more weight than a member with tangential competence. The score breakdown by Dormain is available in the full deliberation record for audit purposes.

---

*v7 — compiled from design sessions.*
*Core additions: §20 Motion Taxonomy & Structured Specification. Format migrated to Markdown.*
*Next: data model sketch (Cell, Commons, motion schema, blind review isolation mechanism).*
