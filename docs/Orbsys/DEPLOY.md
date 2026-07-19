# Orb Sys — Deployment Guide

> How to configure and deploy Orb Sys for each of the nine use cases described
> in the PAAS paper. Each profile covers: recommended Dormain structure, Circle
> architecture, org parameter overrides, membership policy, and specific operational
> notes.

---

## Quick start (any deployment)

```bash
cd infra
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python -m src.scripts.seed \
  --org my-org-slug \
  --org-name "My Organisation" \
  --handle admin \
  --email admin@example.com \
  --password change-me

# Open http://localhost:3000 — login as admin
# Complete bootstrap via POST /org/bootstrap-complete or via the Settings page
```

Production checklist:
- Set `JWT_SECRET_KEY` to a strong random value
- Set `DATABASE_URL` to a managed PostgreSQL instance
- Set `NATS_URL` to a managed NATS cluster (or JetStream on a separate node)
- Set `ANTHROPIC_API_KEY` if you want LLM-powered Insight Engine drafts
- Configure `CORS_ORIGINS` to your frontend domain
- Set `BLIND_DATABASE_URL` (orbsys_blind DB role credentials)

---

## 1. Decentralised Autonomous Organisation (DAO)

**Primary PAAS benefit:** Replaces plutocratic token-weighted voting with
competence-weighted meritocracy. Prevents treasury capture. Gives execution accountability.

### Dormains

```
Protocol Engineering — core smart contract and consensus decisions
Treasury             — fund allocation and budget resolutions
Community            — onboarding, culture, contributor relations
Security             — audit, vulnerability disclosure
Governance           — meta-governance, parameter changes
Research             — proposal research and evidence
```

### Circles

```
Protocol Circle      mandate: Protocol Engineering
Treasury Circle      mandate: Treasury               W_h minimum: 1800 (Finance/Crypto)
Security Circle      mandate: Security               W_h minimum: 2000
Governance Circle    mandate: Governance
Community Circle     mandate: Community
Org Integrity Circle mandate: Governance, Community
Membership Circle    mandate: Community
Judicial Circle      mandate: Governance             W_h minimum: 2400 (Legal/Ethics)
```

### Parameter overrides

```
membership_policy:       open_application
pass_threshold_pct:      0.60   # slightly above majority for protocol changes
novice_slot_floor_pct:   0.35   # strong inclusion signal for token holders converting to contributors
stf_min_size:            4      # larger panels for high-stakes treasury decisions
commons_visibility:      members_only
```

### Operational notes

- Use `hybrid` motions for treasury allocations — the sys_bound block updates
  the budget parameter, the directive block names the executing Treasury Circle
- W_h credential claims should reference on-chain verified identity (ENS, SBT)
  via `vdc_reference` field
- Judicial Circle handles governance capture attempts — the Inferential Engine
  flags coordinated voting patterns as anomalies for jSTF consideration
- For large DAOs (>200 members): create domain-specific Membership Circles with
  separate `membership_policy` parameters per Dormain cluster

---

## 2. Open-Source Software Project

**Primary PAAS benefit:** Formalises the informal meritocracy already present in
most open-source communities. Separates code review (xSTF) from governance (Circle vote).
Protects against maintainer capture and contributor burnout.

### Dormains

```
Core Protocol        — language spec, runtime, breaking changes
Libraries            — standard library, ecosystem packages
Security             — CVE disclosure, dependency audits
Developer Experience — tooling, documentation, onboarding
Community            — code of conduct, contributor relations
Release Management   — versioning policy, deprecation schedules
```

### Circles

```
Core Maintainers     mandate: Core Protocol, Security   W_h minimum: 2200
Libraries Circle     mandate: Libraries
Security Circle      mandate: Security                  W_h minimum: 2000
Community Circle     mandate: Community, Developer Experience
Release Circle       mandate: Release Management
Org Integrity Circle mandate: Governance, Community
```

### Parameter overrides

```
membership_policy:       open_application
pass_threshold_pct:      0.50   # simple majority for most decisions
novice_slot_floor_pct:   0.40   # high — open-source should maximise participation
stf_rotation_weeks_min:  1      # short rotations — many contributors available
stf_rotation_weeks_max:  8
commons_visibility:      public  # open-source transparency
```

### Operational notes

- `commons_visibility: public` — Commons threads are readable by non-members.
  Non-members can post but cannot sponsor. Ideal for pre-RFC community feedback.
- Security Circle should use `invite_only` internally for vulnerability disclosures —
  create a separate `security-private` Cell type for embargoed CVEs
- W_h credentials: GitHub contribution stats, package download counts, conference talks
  can be submitted as `verified_contribution` credential type via vSTF
- xSTF composition for code review: weight toward `Security` and `Core Protocol`
  W_s for changes touching those Dormains
- Maintainer burnout protection: the 30% novice floor and STF rotation schedules
  distribute review load across the contributor pool rather than concentrating on
  a small set of high-W_s maintainers

---

## 3. Decentralised Scientific Research Consortium

**Primary PAAS benefit:** Verifiable external credentials (W_h) anchor the competence
system to real academic expertise. Structured conflict resolution addresses authorship
disputes and data integrity questions. Transparent audit trail satisfies funder requirements.

### Dormains

```
Research Methods     — study design, statistical methodology
Data Science         — analysis pipelines, reproducibility
Domain Science       — the specific scientific field (customise per consortium)
Ethics & IRB         — research ethics, participant protection
Publication          — authorship standards, journal relations
Grant Management     — funding allocation, reporting obligations
```

### Circles

```
Scientific Council   mandate: Research Methods, Domain Science   W_h minimum: 2400 (PhD)
Data Integrity Circle mandate: Data Science, Research Methods    W_h minimum: 2000
Ethics Circle        mandate: Ethics & IRB                       W_h minimum: 2200
Publications Circle  mandate: Publication
Grants Circle        mandate: Grant Management                   W_h minimum: 1800
Org Integrity Circle mandate: Governance, Research Methods
Judicial Circle      mandate: Ethics & IRB, Governance           W_h minimum: 2600
```

### Parameter overrides

```
membership_policy:       invite_only   # verified researchers only
pass_threshold_pct:      0.67          # supermajority for significant decisions
novice_slot_floor_pct:   0.20          # lower — expertise is critical in this context
stf_rotation_weeks_max:  12            # longer mandates for complex research reviews
c_max:                   80            # lower cap — conservative competence movement
```

### Operational notes

- `invite_only` membership: PhD students and postdocs are invited by their institution's
  PI (who holds Circle membership). Their W_h is bootstrapped from their degree credential.
- W_h credential types: `degree` (PhD, MD), `certification` (IRB certification),
  `patent` (research patent), `verified_contribution` (authorship on key papers)
- The Judicial Circle is the primary dispute resolution body for authorship conflicts.
  A jSTF investigation follows the same forensic process as any integrity breach.
- For multi-institution consortia: each institution can have a sub-circle with mandate
  over institution-specific Dormains, reporting to the Scientific Council
- The Integrity Engine's complete audit trail satisfies Open Science Framework (OSF)
  and pre-registration requirements — every decision has a documented rationale

---

## 4. Professional Association

**Primary PAAS benefit:** Dynamic policy development governed by practitioners with
domain expertise. Protection against regulatory capture by sub-groups with narrow
interests. Transparent standard-setting process defensible to external bodies.

### Dormains (example: Medical Association)

```
Clinical Standards   — treatment guidelines, clinical protocols
Research Evidence    — evidence grading, systematic review standards
Ethics & Conduct     — professional ethics, disciplinary standards
Education & Training — CPD requirements, training accreditation
Regulatory Affairs   — government interface, licensing standards
Member Services      — membership benefits, communications
```

### Circles

```
Standards Council    mandate: Clinical Standards, Research Evidence   W_h minimum: 2400
Ethics Committee     mandate: Ethics & Conduct                        W_h minimum: 2200
Education Circle     mandate: Education & Training                    W_h minimum: 2000
Regulatory Circle    mandate: Regulatory Affairs
Member Circle        mandate: Member Services
Org Integrity Circle mandate: Governance
Judicial Circle      mandate: Ethics & Conduct                        W_h minimum: 2600
```

### Parameter overrides

```
membership_policy:       invite_only   # licensed practitioners only
pass_threshold_pct:      0.67          # supermajority for standard changes
novice_slot_floor_pct:   0.25
stf_rotation_weeks_min:  4             # longer mandates — complex policy work
stf_rotation_weeks_max:  12
```

### Operational notes

- W_h credentials: professional license numbers, board certifications, fellowship designations
- For association chapters: create a Circle per chapter with mandate over regional variants
  of relevant Dormains. Cross-chapter coordination via xSTF.
- Disciplinary actions against members go through the Judicial Track. The Meta-aSTF
  ruling is the association's formal disciplinary finding.
- Published resolutions form the association's policy registry — the immutable ledger
  record provides a defensible audit trail for regulatory scrutiny.
- `pass_threshold_pct: 0.67` for standard changes protects against thin majorities
  imposing controversial standards on a divided membership.

---

## 5. Global Non-Profit / NGO

**Primary PAAS benefit:** Accountability in distributed action. Transparent resource
allocation satisfying donor requirements. Clear chains of authority for field offices
without centralised coordination.

### Dormains

```
Programme Design     — intervention design, theory of change
Field Operations     — deployment logistics, field protocols
Finance              — budget management, fiduciary obligations
Monitoring & Eval    — impact measurement, reporting standards
Partnerships         — external partner relations
Communications       — donor reporting, public communications
```

### Circles

```
Programme Circle     mandate: Programme Design, Monitoring & Eval
Operations Circle    mandate: Field Operations
Finance Circle       mandate: Finance                              W_h minimum: 1800
M&E Circle           mandate: Monitoring & Eval, Programme Design
Partnerships Circle  mandate: Partnerships, Communications
Membership Circle    mandate: Field Operations
Org Integrity Circle mandate: Governance
Judicial Circle      mandate: Governance                          W_h minimum: 2400
```

### Parameter overrides

```
membership_policy:       open_application  # field staff can apply
pass_threshold_pct:      0.55
novice_slot_floor_pct:   0.35
commons_visibility:      members_only
stf_rotation_weeks_max:  8
```

### Operational notes

- For distributed field offices: each field office is a Circle with mandate over
  regional operational Dormains. The central Operations Circle has oversight mandate.
- All project execution must cite an enacted Resolution — this creates the audit trail
  donors and regulators require. xSTFs are the executing bodies; the chain of authority
  from Resolution to xSTF to work product is fully logged.
- Finance Circle W_h minimum ensures treasury decisions are made by people with
  genuine financial credentials, not just organisational seniority.
- Field operations during communication blackouts: Circles have full autonomy to
  act within their mandate. The Integrity Engine logs all decisions locally.
  Re-synchronisation is automatic when connectivity is restored.
- Donor reporting: the ledger provides a complete decision history. Every budget
  allocation has a Resolution ID, a voting record, and an aSTF approval.

---

## 6. Internal Research & Development Team / Innovation Lab

**Primary PAAS benefit:** Expert-driven resource allocation replacing bureaucratic
approval processes. Rapid iteration without sacrificing accountability. Knowledge
preservation across team turnover.

### Dormains

```
Product Research     — user research, market analysis
Engineering          — technical architecture, prototyping
Design               — UX/UI, design systems
Data & Analytics     — experimentation, A/B testing, metrics
Strategy             — product direction, competitive analysis
Operations           — project management, tooling
```

### Circles

```
Product Circle       mandate: Product Research, Strategy
Engineering Circle   mandate: Engineering
Design Circle        mandate: Design, Product Research
Analytics Circle     mandate: Data & Analytics
Ops Circle           mandate: Operations
Org Integrity Circle mandate: Governance
```

### Parameter overrides

```
membership_policy:       invite_only   # internal team members only
pass_threshold_pct:      0.50          # move fast — simple majority
novice_slot_floor_pct:   0.30
stf_rotation_weeks_min:  1             # short rotations match sprint cadences
stf_rotation_weeks_max:  4
commons_visibility:      members_only
```

### Operational notes

- `invite_only` but with a lightweight vetting process — new team members are invited
  by their team lead; W_h is bootstrapped from their employment role and track record.
- Resource allocation motions use `hybrid` type: the sys_bound block updates budget
  parameters; the directive block instructs the relevant Circle to execute.
- The Integrity Engine's institutional memory solves the "bus factor" problem —
  every decision has a documented rationale that survives team turnover.
- For organisations using sprint methodology: Cell lifecycles naturally align with
  sprint cycles. Weekly aSTF reviews replace traditional sprint reviews.
- Connect the Insight Engine's LLM backend to internal knowledge bases for
  context-aware draft generation.

---

## 7. Space Society / Science Society

**Primary PAAS benefit:** Curiosity-driven matching surfaces niche domain experts
for highly technical decisions. Competence metrics prevent domination of technical
decisions by administratively active but domain-inexpert members.

### Dormains (example: Mars Society)

```
Mission Architecture — mission design, trajectory planning
Life Support         — ECLSS, habitat engineering
Science Payload      — instrument selection, research priorities
Operations           — mission operations, communication protocols
Education & Outreach — public engagement, STEM programs
Policy & Advocacy    — regulatory affairs, space law
```

### Circles

```
Technical Council    mandate: Mission Architecture, Life Support   W_h minimum: 2200
Science Circle       mandate: Science Payload                      W_h minimum: 2000
Operations Circle    mandate: Operations
Outreach Circle      mandate: Education & Outreach
Policy Circle        mandate: Policy & Advocacy
Org Integrity Circle mandate: Governance
```

### Parameter overrides

```
membership_policy:       open_application
pass_threshold_pct:      0.55
novice_slot_floor_pct:   0.40   # space societies have many passionate non-expert members
stf_rotation_weeks_max:  8
commons_visibility:      public  # public engagement is part of the mission
```

### Operational notes

- `commons_visibility: public` — the public can read and post in Commons. Non-members
  engage with the community but cannot sponsor motions or vote.
- `novice_slot_floor_pct: 0.40` ensures passionate student members and early-career
  engineers have genuine participation opportunities, not just observer status.
- Curiosity signals (B_u) are especially valuable here — members with high curiosity
  in niche technical Dormains (e.g., in-situ resource utilisation) are surfaced for
  relevant Cells even before they've built significant W_s.
- Technical Council W_h minimum: engineering degrees, flight heritage, published research.
  This protects mission-critical decisions from governance by enthusiasm alone.

---

## 8. Holacratic or Sociocratic Organisation Upgrade

**Primary PAAS benefit:** Adds independent audit and conflict resolution to existing
distributed governance structures. Addresses the known failure modes of Holacracy
(familiarity bias, scope limitation, weak accountability enforcement).

### Migration from Holacracy

Holacracy circles map directly to PAAS Circles. Holacracy roles map to Dormain expertise.
The governance difference: PAAS adds an external audit layer (aSTF) that Holacracy lacks.

```
Holacracy Circle     → PAAS Circle (same name, same mandate)
Holacracy Role       → Dormain (name the domain of expertise)
Lead Link            → Circle member with highest W_s in primary Dormain
Rep Link             → Member invited to cross-circle xSTF
Governance Meeting   → Cell with crystallise → motion → vote lifecycle
Tactical Meeting     → Commons thread → Cell (no motion needed if operational)
```

### Dormains

Map your existing Holacracy role taxonomy to Dormains. Start with one Dormain per
major function, then split as the community develops more granular competence signals.

### Circles

Preserve your existing circle structure. Add:
```
Org Integrity Circle  — competence verification, vSTF commissioning
Judicial Circle       — replaces Holacracy's constitution interpretation process
```

### Parameter overrides

```
membership_policy:       invite_only   # existing team members invited
pass_threshold_pct:      0.50          # Holacracy uses consent-based — simple majority is close
novice_slot_floor_pct:   0.25
stf_rotation_weeks_min:  2
stf_rotation_weeks_max:  6
```

### Operational notes

- The critical addition: aSTFs provide the external accountability that Holacracy's
  internal tension resolution process cannot. An aSTF can reject a Circle decision
  even if the Circle reached internal consent.
- Holacracy's "objection" process maps to the aSTF `revision_request` verdict.
- Constitution interpretation disputes go to the Judicial Circle (jSTF), replacing
  the Holacracy practitioner network's informal arbitration.
- W_s bootstrapping: existing role assignments become initial W_s scores. Members
  holding a role for >1 year start at W_s ≈ 1200 in the relevant Dormain.
  A vSTF verifies these initial scores over the first two months.

---

## 9. Global Non-Territorial Organisation

**Primary PAAS benefit:** Adaptive governance for purpose-driven collectives with no
fixed hierarchy and geographically distributed membership. Competence-based allocation
responds to evolving goals faster than any fixed organisational chart.

### Dormains

Define Dormains around the organisation's mission dimensions, not its structure.
Example (climate action network):

```
Climate Science      — scientific evidence, modelling, projections
Policy & Advocacy    — regulatory engagement, policy design
Financing            — climate finance, carbon markets, investment
Community Resilience — adaptation, frontline communities
Technology           — clean energy, carbon removal technologies
Communications       — narrative strategy, media, public engagement
```

### Circles

```
Science Circle       mandate: Climate Science             W_h minimum: 2000
Policy Circle        mandate: Policy & Advocacy
Finance Circle       mandate: Financing                   W_h minimum: 1800
Resilience Circle    mandate: Community Resilience
Technology Circle    mandate: Technology
Communications Circle mandate: Communications
Membership Circle    mandate: Community Resilience (onboarding)
Org Integrity Circle mandate: Governance
Judicial Circle      mandate: Governance                  W_h minimum: 2400
```

### Parameter overrides

```
membership_policy:       open_application
pass_threshold_pct:      0.55
novice_slot_floor_pct:   0.40   # large, diverse membership base
stf_rotation_weeks_max:  10     # longer mandates accommodate global time zones
commons_visibility:      public
```

### Operational notes

- For very large membership (>500): set `stf_min_size: 5` and `stf_max_size: 11`
  to maintain quorum depth at scale.
- `commons_visibility: public` — transparency is core to the mission.
  Non-members can engage in Commons and build B_u signals before applying.
- For multi-language communities: the Insight Engine draft generation uses whatever
  LLM backend you configure — multilingual models work out of the box.
- Time zone accommodation: async voting is the default. Circle votes stay open for
  72 hours by default; adjust `quorum_pct` and vote window via org parameters.
- Decentralised field nodes: each regional hub is a Circle. Cross-hub coordination
  uses xSTFs with representatives from each relevant Circle. The ledger provides
  a single source of truth accessible to all nodes regardless of location.
- Crisis resilience: when global connectivity is interrupted, each Circle continues
  operating autonomously under its existing mandate. The Integrity Engine logs locally.
  Re-synchronisation after reconnection is automatic — the hash chain verifies
  integrity of the offline period's decisions.

---

## General deployment notes

### Scaling org parameters

All org parameters are governed — changing them requires a `sys_bound` motion through
the full governance lifecycle. This is intentional: parameter stability is a governance
property, not an administrative convenience.

For the initial bootstrap period (first 90 days), the seed defaults are conservative:
- `novice_slot_floor_pct: 0.30` — adjust up if you want stronger inclusion
- `pass_threshold_pct: 0.50` — adjust up for higher-stakes contexts
- `stf_rotation_weeks_max: 12` — adjust down for faster-moving contexts

### Multi-org installations

A single Orb Sys installation can host multiple independent organisations.
Each org has full isolation (separate DB rows via RLS, separate NATS streams,
separate ledger chains). The `org_slug` in URLs identifies the tenant.

### Monitoring

Key signals to watch:
- `GET /ledger/verify` — chain must always return `status: ok`
- Anomaly flags in `GET /ledger?event_type=anomaly_flagged` — review weekly
- STF pending_audit count — competence spikes that haven't been reviewed
- Circle health scores in `GET /circles/:id/health` — declining Gate 1 approval
  rate is a leading indicator of Circle dysfunction

### Data retention

The ledger is append-only and intended to be permanent. Resolutions are immutable.
Member exit records are permanent. The GDPR right-to-erasure applies to personal data
in `members` and `member_applications` — implement a pseudonymisation process for
handle and email fields on member exit.
