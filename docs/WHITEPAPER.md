# Orb Sys
## A Reference Implementation of the Polycentric Autonomy-Audit System

**Version 1.0**  
Built on PAAS by Okitoi Samuel Oumo (2025)

---

## Abstract

Orb Sys is an open-source governance platform implementing the Polycentric Autonomy-Audit System (PAAS) — a socio-technical framework for legitimate, adaptive governance in fluid, trust-sparse organisations. Where most governance software asks *who should decide*, PAAS asks *who has demonstrated the competence to decide this particular thing*, and Orb Sys answers that question in real time.

The system replaces positional authority with a continuous, evidence-based competence economy. Influence is earned through peer-reviewed contribution, anchored by verifiable external credentials, and audited independently after every significant decision. The result is an organisation that is simultaneously more expert-driven and more resistant to capture than either traditional hierarchies or token-weighted democracies.

This document describes what Orb Sys is, the problem it solves, how its core mechanisms work, and how it is deployed. It is intended for founders, governance researchers, and operators considering Orb Sys for their community.

The academic framework underlying Orb Sys is documented separately in *A Polycentric Autonomy-Audit System for Participatory Meritocracy and Anti-Fragile Governance in Fluid Collectives* (Oumo, 2025).

---

## 1. The Problem

Every organisation eventually faces the same tension: decisions need to be made by people who understand them, but the people who understand them rarely hold the formal authority to make them. The gap between expertise and authority is where governance fails.

This failure takes predictable forms.

**In traditional hierarchies,** decisions wait for approvals from people who have authority but not expertise. By the time a decision reaches someone with the formal power to make it, the people who understand it have been filtered out. The result is slow, low-quality decisions made by the wrong people, defended by the right ones.

**In token-weighted DAOs,** influence is proportional to financial stake. Large token holders dominate regardless of their understanding of the decision at hand. The result is governance capture by the wealthy — not meritocracy, but plutocracy with better branding.

**In consensus-based systems** (Holacracy, Sociocracy, flat management), informal power structures fill the vacuum left by the absence of formal ones. The loudest voices, the most persistent members, and the people with the most time dominate. Expertise is diluted into consensus.

**In purely algorithmic governance,** the algorithm becomes the authority. It cannot adapt to novel situations, cannot resolve genuine ethical disputes, and cannot be held accountable when it produces unjust outcomes.

Each model also fails along a second dimension: accountability after decisions are made. Governance systems typically focus on *how* decisions are reached (voting mechanisms, consensus processes) while leaving *who is responsible for implementing them* vague. The result is that decisions pass but nothing happens — or something happens, but not what was decided.

Orb Sys addresses both dimensions simultaneously.

---

## 2. The PAAS Foundation

Orb Sys is built on the Polycentric Autonomy-Audit System (PAAS), a governance framework engineered specifically for fluid, non-territorial communities — DAOs, open-source projects, research consortia, professional associations, and any other organisation that operates without fixed geographic boundaries or traditional legal structures.

PAAS is grounded in three core principles:

**Participatory meritocracy.** Influence is proportional to demonstrated expertise in the specific domain under discussion — not to tenure, not to financial stake, not to social capital. A new member with genuine domain expertise has more voting weight than a long-standing member without it, in that domain and for that decision.

**Structural audit independence.** Every significant decision is reviewed by an independent body that was not involved in making it. This is not a soft cultural norm — it is structurally enforced. The body that decides cannot be the body that audits. The body that investigates cannot be the body that adjudicates. Separation of powers is architectural, not aspirational.

**Anti-fragility.** The system is designed to grow stronger under stress. Governance challenges — contested decisions, boundary disputes, bad actors, coordination failures — are channelled into structured resolution processes that produce public records. Those records become institutional memory. The organisation learns from every stress rather than fragmenting under it.

---

## 3. Core Mechanisms

### 3.1 The Competence Economy

Every member of an Orb Sys organisation maintains a competence profile — a vector of scores across the organisation's knowledge domains (Dormains). These scores are not assigned; they are earned.

**Soft Competence (W_s)** is the dynamic, contribution-based component. It grows when a member contributes to formal governance processes — deliberation cells, competence-weighted votes, audit reviews — and those contributions are endorsed by other members with demonstrated expertise in the same domain. The endorsement is weighted by the endorser's own competence: an expert's positive assessment carries more weight than a novice's. It decays when a member stops contributing, reflecting the perishable nature of active expertise.

**Hard Competence (W_h)** is the static, credential-anchored component. It is derived from verifiable external credentials — academic degrees, professional certifications, patents, licences — and verified through a blind peer review process by members with existing expertise in the same domain. W_h provides an external anchor that prevents the system from developing insular biases, and it gates access to roles where foundational verified expertise is non-negotiable (judicial panels, high-stakes financial and security decisions).

When a member votes, their vote is weighted by their Soft Competence in the domain most relevant to the decision at hand. A member with deep expertise in cryptographic protocol design has a decisive vote on protocol decisions; their opinion on community onboarding policy carries less weight, and appropriately so. This is not a second-class status — it is domain specificity.

The same member may simultaneously hold high competence in three domains, serving as a primary decision-maker in each. The system routes each decision to the right expertise rather than routing all decisions through the same hierarchy.

### 3.2 Circles: Autonomy with Accountability

A Circle is a closed, competence-gated body with decision-making authority and implementation responsibility within a specific domain. Circles are the primary locus of governance action.

What makes Circles distinctive is their dual mandate: they not only decide, they implement. The people who vote on a motion are the same people responsible for executing it. There is no gap between decision and accountability.

Within their domain, Circles act without seeking permission from a higher authority. This is the autonomy half of PAAS. A Security Circle can commission an audit, a Treasury Circle can allocate funds, a Protocol Circle can commission a technical review — all without waiting for approval from above, because there is no above. Authority is distributed across domains, not concentrated in a hierarchy.

The check on this autonomy is not a veto from a higher power. It is an audit from an independent peer body.

### 3.3 Short-Term Facilitators: The Audit Layer

A Short-Term Facilitator (STF) is a temporary body with a specific mandate. It forms, executes its task, and dissolves. There are no permanent audit committees in Orb Sys — only rotating, task-specific panels.

Four types:

**Audit STF (aSTF)** — the primary governance safety mechanism. After a Circle votes on a motion, an independently selected panel reviews the decision for process soundness, evidence quality, conflicts of interest, and alignment with the organisation's founding principles. The aSTF can approve (the motion becomes a Resolution), reject (the motion returns with a public rationale), or issue a revision request (the deliberation cell reactivates with specific guidance). The aSTF does not participate in deliberation — it reviews after the fact, ensuring its independence.

**Executional STF (xSTF)** — a project team. Commissioned to execute research, draft proposals, conduct technical reviews, or mediate between Circles on cross-domain matters. Reports to the commissioning Circle and dissolves when the task is complete.

**Verification STF (vSTF)** — the credential verification body. When a member submits a W_h credential claim, a panel of members with existing expertise in the relevant domain independently reviews the evidence, blind to each other's assessments. The aggregate verdict determines the member's verified Hard Competence.

**Judicial STF (jSTF)** — the integrity body. Investigates serious breaches: coordinated manipulation attempts, competence misrepresentation, bad-faith governance. The investigation is conducted by a neutral panel; the ruling is issued by a separate Meta-aSTF that audits the investigation itself for due process and proportionality. The separation between investigation and adjudication is the core anti-capture mechanism.

All STF reviewer identities are permanently sealed in the record — not as a permission restriction, but structurally: the `stf_verdicts` table has no `reviewer_id` column. There is nothing to expose. This protects reviewers from social pressure and retaliation, and prevents audit manipulation by removing the target entirely.

### 3.4 The Governance Lifecycle

Every significant decision in Orb Sys follows the same path:

**Commons** — the open discussion space. Ideas form here. All members can read and post; in public-visibility organisations, non-members can as well. A Commons thread accumulates perspective before any formal governance begins.

**Sponsorship** — a Circle member whose domain mandate covers the thread converts it into a formal Deliberation Cell. This is a commitment: the sponsor takes accountability for the proposal entering the governance stream.

**Cell** — the structured deliberation workspace. Invited Circles deliberate asynchronously. The Insight Engine produces rolling minutes summarising key positions, open questions, and emerging consensus, reducing the cognitive load of following parallel discussions. When deliberation is ready, a Circle member crystallises the discussion into a motion.

**Vote** — the motion is voted on by the deliberating Circles, weighted by each member's Soft Competence in the relevant domain. Simple majority for routine decisions; configurable supermajority for high-stakes ones.

**Gate 1 (aSTF)** — an independently selected audit panel reviews the decision. If approved, the motion becomes a Resolution. If rejected, a public rationale is written into the permanent record and the Cell can reopen with the aSTF's guidance attached.

**Implementation** — the approved Resolution names the Circle or Circles responsible for execution. That Circle implements.

**Gate 2** — for parameter changes, the Integrity Engine performs an automated diff: the applied values must match the Resolution specification exactly. For directive decisions, an interpretive audit assesses whether implementation was faithful. A mismatch produces a `Contested` status, not a silent failure.

**Immutable record** — every step of this process is logged in a tamper-evident ledger with a SHA-256 hash chain. The record of what was decided, who decided it, who reviewed it, and how it was implemented is permanent and publicly verifiable within the organisation.

### 3.5 The Intelligence Layer

Three engine services run continuously alongside the governance platform:

**Integrity Engine** — the ledger guardian and sole writer of competence scores. Computes ΔC from formal review events, applies W_h boosts on credential verification, executes system parameter changes atomically when Resolutions are enacted, detects anomalies (competence spikes, coordinated endorsement patterns, voting weight concentration), and maintains the hash chain. It is the only service with write access to the ledger and competence tables.

**Inferential Engine** — the routing and matching layer. Matches members to relevant deliberation cells and STF roles based on their competence profile and declared interests (Curiosity vectors). Tags Commons threads with relevant domains. Flags when a deliberation cell lacks coverage in domains relevant to its subject matter, and biases aSTF composition to fill those gaps. When a member submits a credential claim, the Inferential Engine commissions the vSTF that will verify it.

**Insight Engine** — the cognitive load reducer. Generates on-demand draft proposals from Commons threads when a member sponsors them. Produces rolling structured minutes from Cell deliberations. Monitors STF deadlines and sends notifications. All draft generation is on-demand only — triggered by a human action, not proactively. The Insight Engine has zero prescriptive power; it summarises and drafts, it does not decide.

The AI layer is intentionally non-prescriptive. It may suggest, summarise, and schedule. It may not recommend a vote, edit a proposal without explicit human direction, or unilaterally alter a governance outcome. Human judgment is the output, not an input to an algorithm.

---

## 4. What Orb Sys Is Not

**It is not a voting app.** Voting is one step in a multi-stage process. The weight of each vote is determined by demonstrated competence in the relevant domain. The outcome is audited after the vote. The result is immutably recorded and accountably implemented.

**It is not a DAO platform.** DAOs use token-weighted voting. Orb Sys uses competence-weighted voting. In a DAO, a large token holder has outsized influence regardless of expertise. In Orb Sys, influence requires demonstrated contribution in the specific domain under discussion. These are fundamentally different models.

**It is not a project management tool.** Orb Sys governs decisions. It does not manage tasks, timelines, or deliverables. Circles commission xSTFs for specific work; the work product is reported back to the Circle; the governance decision is about what to do, not how to track that it got done.

**It is not a consensus machine.** Orb Sys does not seek unanimity. It seeks quality decisions by the people best positioned to make them, reviewed by independent peers, with full accountability for implementation. Dissent is recorded and respected; it does not veto.

**It is not autonomous.** Orb Sys augments human governance; it does not replace it. Every governance action requires a human to initiate, deliberate, vote, review, or implement. The engine layer reduces coordination friction and cognitive load. It does not govern.

---

## 5. Who It Is For

Orb Sys is designed for organisations where:

- **Expertise is distributed** and the people who best understand a decision are not the same people who currently hold formal authority over it
- **Trust is sparse** — members may not know each other, may be geographically distributed, or may have legitimate competing interests
- **Membership is fluid** — people join and leave; the organisation's identity must survive leadership turnover
- **Accountability matters** — decisions need an auditable trail that can be examined by members, funders, regulators, or the public
- **Capture is a real risk** — there are parties who would benefit from controlling governance outcomes, and the system must structurally resist them

Orb Sys has been deployed in nine governance archetypes, described in the deployment guide. These include decentralised autonomous organisations, open-source projects, research consortia, professional associations, NGOs, R&D teams, scientific societies, organisations migrating from Holacracy or Sociocracy, and global non-territorial collectives.

---

## 6. First-Run Experience

A new Orb Sys installation begins with a template selection. Five primary templates represent the most common governance contexts: Community Collective, DAO/Crypto Network, Research Consortium, Professional Association, and Open-Source Project. Extended templates cover NGOs, R&D labs, cooperatives, Holacracy migrations, and multi-stakeholder platforms.

Each template seeds the organisation with:

- A set of general knowledge domains that the founding circle will rename to match the organisation's actual vocabulary
- Governance parameter defaults calibrated to the archetype (voting thresholds, novice participation floors, credential requirements)
- A queue of founding proposals — open questions for the founding circle to deliberate

The founding circle is not appointed. It forms through the credential verification process itself: as early members submit and verify their credentials, those with demonstrated competence are recommended for founding circle candidacy. When enough verified members have been recommended (the threshold scales with the organisation's size estimate), the founding circle forms automatically and the governance workspace opens.

The first thing the founding circle does is govern. The pre-seeded proposals are genuine deliberation cells — open questions about the organisation's identity, circle structure, voting thresholds, and membership policy. The founding circle files real motions that go through real Gate 1 aSTF review. By the time `bootstrap_complete` is enacted and the founding circle dissolves, every member has used the governance system to define the organisation it will become.

---

## 7. Technical Architecture

Orb Sys is a full-stack open-source application.

```
apps/
  api/          FastAPI backend — 69 governance routes
  blind/        Blind Review API — structurally isolated, no reviewer identity columns
  web/          Next.js 15 frontend — 18 governance pages

services/
  integrity/    Sole ledger and competence writer — Python asyncio
  inferential/  Routing, matching, and composition — Python asyncio
  insight/      Drafts, minutes, notifications — Python asyncio

infra/
  docker-compose.yml    Full local stack
  postgres/             DB role setup, append-only triggers
```

**Database:** PostgreSQL 16 with Alembic migrations. All governance tables are append-only (UPDATE and DELETE are rejected at the trigger level). Every `ledger_events` row carries a SHA-256 hash of its predecessor — tampering is detectable from the first modified row. Five DB roles enforce access control at the connection level: the Blind Review service role cannot perform the join that would expose reviewer identities, because the join is structurally impossible (no column to join on).

**Event routing:** NATS JetStream. All governance actions emit events to a per-org stream. All three engine services are durable subscribers. This means the main API is always fast (emit and return); heavy computation happens asynchronously in the engines. One exception: sys_bound resolution enactment is synchronous — the API awaits the Integrity Engine's atomic write and returns the result.

**Authentication:** Two structurally incompatible JWT token types. Session tokens are rejected by the Blind Review API with 403 (not 401); isolated view tokens are rejected by the main API. Wrong token type is an access control failure, not an authentication failure.

**LLM integration:** The Insight Engine uses Anthropic's Claude for draft generation, minutes summarisation, and STF assignment notifications. All calls are prompt-only — the LLM cannot read the database, cannot emit governance events, and cannot influence any outcome without a human confirming the draft. The system degrades gracefully to rule-based drafting when the API key is absent.

---

## 8. Governance of the Governance System

Orb Sys organisations govern themselves. The system's parameters — voting thresholds, novice participation floors, STF rotation windows, membership policy, credential requirements per domain — are all governed via the standard governance lifecycle. Changing `pass_threshold_pct` from 0.50 to 0.67 requires a `sys_bound` motion through Commons → Cell → vote → Gate 1 aSTF → Resolution → enacted. There is no administrative backdoor.

This has an important consequence: the governance system is resistant to unilateral change by any single actor, including the system's own operators. An operator cannot change a threshold, a membership policy, or an audit requirement without going through the governance process that the rest of the membership can see and contest.

The Integrity Engine enforces this mechanically: it is the sole writer of system parameters, and it writes them only on the basis of enacted Resolutions. A Circle member cannot directly update `org_parameters`. A database administrator running a direct SQL update would break the hash chain, making the tampering detectable by any member running `GET /ledger/verify`.

---

## 9. Security Model

Orb Sys is designed with a specific threat model: actors who would attempt to gain illegitimate influence over governance outcomes.

**Sybil resistance:** Hard Competence (W_h) requires costly, auditable external verification — a vSTF blind-reviews actual credential documents. A Sybil attacker creating multiple identities would face the same verification burden for each. Soft Competence requires sustained, audited contribution — coordinated fake accounts cannot bootstrap meaningful W_s without producing genuine reviewed work.

**Capture resistance:** The dual-layer STF mechanism means an attacker must simultaneously compromise both the deliberating Circle and the independent aSTF to control an outcome. The aSTF's composition is determined after the motion is filed, weighted toward members not involved in the deliberation, with identities sealed. There is no known composition to target before the panel is formed.

**Endorsement ring detection:** The Integrity Engine tracks correlation between endorsers across multiple instances. Reviewers whose endorsements consistently diverge from later audit findings have their effective weight reduced. Coordinated mutual endorsement rings — where a group inflates each other's W_s — are flagged as anomalies and routed to the Judicial Track.

**Ledger integrity:** The hash chain makes retroactive tampering detectable. The chain is verifiable by any active member at any time. Editing a ledger row breaks the chain at that row and every row thereafter.

**Reviewer identity protection:** STF reviewer identities are absent from the verdict table — not hidden behind a permission flag, structurally absent. This eliminates the attack surface entirely.

---

## 10. Open Source

Orb Sys is fully open source. The codebase, documentation, deployment guides, and PAAS interpretation decisions are published under an open licence.

**Why open source matters for governance software.** A governance system whose own code is opaque is asking its users to trust the operator as much as they trust the governance process. That is incompatible with the spirit of PAAS. The Integrity Engine's competence computation, the Inferential Engine's candidate scoring, and the aSTF composition algorithm must all be publicly auditable — not just in principle, but in the actual deployed code.

**Contributing.** Orb Sys welcomes contributions across the full stack — API services, engine logic, frontend components, documentation, and the agent simulation scenarios that serve as governance regression tests. The contribution process itself uses Orb Sys: significant changes to the reference implementation are proposed and reviewed through the project's own governance workspace.

---

## 11. Relationship to the PAAS Paper

Orb Sys is a reference implementation, not a canonical one. The PAAS paper defines the framework; Orb Sys is one way to instantiate it. Several implementation decisions in Orb Sys extend, operationalise, or deliberately depart from the paper's specifications. These decisions are documented in full in `docs/PAAS_INTERPRETATIONS.md`.

The most significant departure is the aSTF verdict: the paper specifies a binary outcome (Approve or Reject), while Orb Sys adds a third option (Revision Request) that reactivates the deliberation cell with specific guidance rather than forcing a full resubmission. This reduces friction for near-complete motions while preserving the accountability trail.

Operators implementing PAAS via Orb Sys should read the interpretations document and consider which decisions they want to adopt as-is versus revisit for their specific context. Several implementation parameters (Gate 2 timing, novice slot floor scope, aSTF composition balancer weights) are org-governed and can be adjusted through the normal governance lifecycle after bootstrap.

---

## 12. Getting Started

**System requirements:** Docker, Docker Compose, 4GB RAM minimum.

```bash
git clone https://github.com/orbsys/orbsys
cd orbsys/infra
docker compose up -d
docker compose exec api alembic upgrade head

# Open http://localhost:3000
# Select a template, set your expected org size, register as the first member
```

On first run, the browser opens to the template selector. Choose the archetype closest to your organisation, set an approximate member count (this calibrates founding circle size), register your account, and share the invite link with your founding members. The governance workspace opens automatically when the founding circle forms.

For production deployments, the deployment guide (`docs/DEPLOY.md`) covers configuration for each of the nine supported use cases, including parameter recommendations, credential type guidance, and operational notes specific to each archetype.

---

## Appendix: Key Terms

**Circle** — A closed, competence-gated body with both decision-making authority and implementation responsibility within a specific domain.

**Cell** — A temporary deliberation workspace. Not a decision-making body — deliberation happens here; decisions happen in Circle votes.

**Commons** — The open discussion space where ideas form before entering formal governance.

**Curiosity (B_u)** — Self-declared interest signals. Used for matching members to relevant cells and roles. Zero effect on vote weight.

**Dormain** — A knowledge domain (e.g., Security, Treasury, Protocol Engineering). All competence scores are domain-specific.

**Hard Competence (W_h)** — Verified external credentials. Gates access to high-stakes roles. Anchors the competence system against purely internal biases.

**Resolution** — An enacted motion. Immutable ledger record. Cannot be amended — only superseded by a new Resolution.

**Short-Term Facilitator (STF)** — A temporary task body. Types: aSTF (audit), xSTF (execution), vSTF (credential verification), jSTF (judicial).

**Soft Competence (W_s)** — Dynamic contribution-based competence. Grows through peer-reviewed governance participation. Decays with inactivity. The primary vote weight.

**Sponsorship** — A Circle member's commitment to elevate a Commons discussion into a formal Deliberation Cell.

---

*Orb Sys is the open-source reference implementation of PAAS.*  
*PAAS framework: Okitoi Samuel Oumo, 2025.*  
*Orb Sys implementation: open source, MIT licence.*
