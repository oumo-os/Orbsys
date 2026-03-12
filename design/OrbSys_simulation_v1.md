# Orb Sys — Agent-Based Simulation Parameters
## v1.0

> Pre-deployment stress testing for the governance model and parameter
> choices. Defines agent archetypes, scenario sets, success metrics,
> and parameter sensitivity ranges for simulation before any real
> community goes live.
>
> Cross-reference: OrbSys_engines_v2.md, OrbSys_datamodel_v1.md,
> PAAS source §X (default parameters), §XII (future research)

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Agent Archetypes](#2-agent-archetypes)
3. [Org Configuration Profiles](#3-org-configuration-profiles)
4. [Scenario Set](#4-scenario-set)
5. [Parameter Sensitivity Ranges](#5-parameter-sensitivity-ranges)
6. [Success & Failure Metrics](#6-success--failure-metrics)
7. [Simulation Outputs](#7-simulation-outputs)
8. [Known Fragility Points](#8-known-fragility-points)

---

## 1. Purpose & Scope

The simulation serves three goals:

**Goal 1 — Parameter validation.**
The default org parameters (novice floor 30%, rotation window 2–12 weeks,
K-factors, G-values, decay rates) are theoretically derived. Before any
real community adopts them, they should be stress-tested across org sizes,
participation distributions, and adversarial scenarios. The simulation
surfaces regimes where the defaults produce pathological outcomes.

**Goal 2 — Attack surface mapping.**
PAAS makes specific claims about resistance to elite closure, Sybil attack,
auditor capture, and collusion. These claims should be verified empirically
through simulation before being made to real communities.

**Goal 3 — Bootstrapping confidence.**
The v2 bootstrapping flow depends on the preliminary W_h pool being large
enough and diverse enough to form valid vSTF reviewer sets. The simulation
should identify the minimum viable founding pool size and composition for
the bootstrap to work without deadlock.

---

## 2. Agent Archetypes

Eight agent types covering the realistic population of any governance system.
Each agent has a base behavioural profile with configurable variance.

---

### Archetype A — The Genuine Contributor

```
profile:
  motivation:     intrinsic — cares about outcomes, not scores
  contribution:   consistent, domain-focused, evidence-cited
  STF behaviour:  honest scoring, completes assignments on time
  vote behaviour: votes in line with stated position in deliberation
  W_s trajectory: grows steadily, converges toward true expertise level

simulation parameters:
  contribution_rate:     high (3–5 formal contributions / active cycle)
  review_quality:        high (S_r correlates with actual contribution quality)
  STF_completion_rate:   0.95
  vote_consistency:      0.90 (occasional genuine position shift)
  defection_probability: 0.02
```

---

### Archetype B — The Passive Member

```
profile:
  motivation:     present but low-engagement
  contribution:   occasional, low-signal
  STF behaviour:  accepts assignments reluctantly, sometimes misses deadlines
  vote behaviour: abstains or follows apparent consensus
  W_s trajectory: slowly grows to a low plateau, high decay vulnerability

simulation parameters:
  contribution_rate:     low (0–1 formal contributions / active cycle)
  review_quality:        neutral (S_r clusters around 0.5)
  STF_completion_rate:   0.60
  vote_consistency:      0.60
  defection_probability: 0.01
```

---

### Archetype C — The Status Seeker

```
profile:
  motivation:     extrinsic — wants Circle membership and vote weight
  contribution:   strategically timed, volume-optimised, quality variable
  STF behaviour:  accepts all assignments (maximises formal review events),
                  completes quickly but not always carefully
  vote behaviour: votes with high-W_s members to build social capital
  W_s trajectory: grows faster than genuine expertise warrants at first,
                  then plateaus when K drops and review quality is exposed

simulation parameters:
  contribution_rate:     very high (6–10 / active cycle)
  review_quality:        positively biased (S_r inflated for prominent members)
  STF_completion_rate:   0.92
  vote_consistency:      follows_high_ws (70% probability of matching top voter)
  defection_probability: 0.15 (shifts allegiance as W_s dynamics change)
```

**Key test:** does the ΔC formula's competence-weighted reviewer pool
(w_r,d weighting) suppress the Status Seeker's inflated scores over time?
If genuine contributors with high W_s give accurate reviews, the Status
Seeker's score should revert toward true expertise level as K decreases.

---

### Archetype D — The Coalition Builder

```
profile:
  motivation:     factional — builds a bloc of aligned members
  contribution:   high quality within bloc's interest areas, selective elsewhere
  STF behaviour:  manipulates reviewer composition where possible
                  (attempts to nominate bloc members for aSTF slots)
  vote behaviour: coordinates votes within coalition (near-perfect consistency
                  across bloc members on issues that matter to coalition)
  W_s trajectory: grows legitimately in coalition's Dormains; uses M_cmp
                  amplification within bloc's Circle

simulation parameters:
  coalition_size:          3–8 agents
  intra_coalition_S_r:     0.85 average (mutual inflation)
  extra_coalition_S_r:     0.45 average (mild suppression of outsiders)
  STF_nomination_bias:     0.70 (favours bloc members when can influence)
  coordination_latency:    1–3 simulation ticks (coalition needs time to align)
  defection_probability:   0.05 within coalition
```

**Key test:** does the auditor-auditee correlation anomaly detector (TYPE 2)
catch the mutual inflation pattern? Does the blind parallel aSTF process
prevent the STF nomination manipulation from distorting Gate 1 outcomes?
Does the Coalition Builder's influence plateau once the anomaly detector fires?

---

### Archetype E — The Sybil Attacker

```
profile:
  motivation:     adversarial — creates fake identity clusters to amplify
                  vote weight or flood the novice STF pool
  contribution:   coordinated across fake accounts, artificially inflated
  STF behaviour:  uses fake accounts to populate STF slots
  vote behaviour: coordinated block voting across all controlled accounts
  W_s trajectory: attempts rapid artificial inflation via mutual reviews

simulation parameters:
  sybil_cluster_size:     3–15 accounts
  coordination_fidelity:  0.95 (near-perfect coordination — same actor)
  activity_timing_delta:  0–30 minute variance (same actor, slightly varied)
  proof_of_personhood:    varies by org config (weak/strong PoP affects viability)
  W_h_falsification:      attempted on 40% of Sybil accounts
```

**Key test:** does the TYPE 3 anomaly detector (correlated voting + improbable
competence growth curves) catch the cluster before it gains meaningful W_s?
Does proof-of-personhood strength change the viable attack surface?
At what Sybil cluster size does the system's detection rate drop below 90%?

---

### Archetype F — The Captured Auditor

```
profile:
  motivation:     corrupt — systematically favours or penalises specific
                  members or Circles in aSTF reviews
  contribution:   normal (cover behaviour)
  STF behaviour:  consistently biased verdicts (approval for allies,
                  rejection/revision_request for targets)
  vote behaviour: normal
  W_s trajectory: normal (corruption is in STF role, not vote weight)

simulation parameters:
  bias_direction:      directional (favours coalition, penalises targets)
  bias_magnitude:      0.30–0.60 (fraction of verdicts that are biased)
  cover_rate:          0.40 (fraction of assignments handled honestly to avoid detection)
  colluding_auditors:  1–3 (single vs. coordinated capture attempt)
```

**Key test:** at what bias magnitude and cover rate does the TYPE 2
anomaly detector (auditor-auditee correlation across multiple STF instances)
surface the pattern? Does the blind parallel structure slow detection by
preventing direct coordination between captured auditors? What is the
maximum damage (Resolutions wrongly approved/rejected) before detection?

---

### Archetype G — The Burnout Risk

```
profile:
  motivation:     genuinely committed but vulnerable to overload
  contribution:   very high initially, drops sharply after burnout event
  STF behaviour:  accepts all invitations, quality degrades under load
  vote behaviour: increasingly cursory
  W_s trajectory: rapid early growth, then sharp W_s decay from inactivity
                  following burnout event

simulation parameters:
  initial_contribution_rate:  very high (8–12 / active cycle)
  burnout_threshold:          configurable (triggered by notification load
                               + concurrent STF count exceeding capacity)
  post_burnout_activity:      near zero for 4–8 simulation cycles
  recovery_probability:       0.60 (40% churn permanently)
  STF_deadline_miss_rate:     0.30 post-burnout
```

**Key test:** do the Insight Engine burnout guardrails (notification caps,
rotation window enforcement, burnout-check before STF assignment) reduce
the burnout event frequency? What parameter regime produces the best
balance between high engagement and sustainable participation?
What is the org-level effect of simultaneously burning out 10% of high-W_s members?

---

### Archetype H — The Legitimate Dissenter

```
profile:
  motivation:     principled — disagrees with majority positions based on
                  genuine alternative expertise or values
  contribution:   high quality, minority positions, well-evidenced
  STF behaviour:  honest, thorough, sometimes issues Revision Requests
                  where others would Approve
  vote behaviour: consistent with stated positions (high integrity)
  W_s trajectory: grows legitimately; may plateau if domain is narrow

simulation parameters:
  position_divergence:     0.70 (diverges from majority 70% of time)
  evidence_quality:        high (0.85 average review quality from others)
  STF_revision_rate:       0.35 (higher than average — thorough reviewer)
  social_isolation_risk:   moderate (may be excluded from Coalition Builder blocs)
```

**Key test:** does the competence-weighted system protect the Legitimate
Dissenter's influence from social suppression? Does the novice-slot floor
ensure diverse perspectives continue to enter the system even when dominant
Circles have high W_s concentration? Does the aSTF composition balancer
surface the Dissenter's expertise when it fills a gap?

---

## 3. Org Configuration Profiles

Four org profiles covering the realistic deployment range.

```
PROFILE 1 — Small Cohesive (30–80 members)
  dormains:       3–5
  circles:        3–4
  archetype_mix:  60% A, 20% B, 10% C, 5% D, 5% others
  W_s_distribution: concentrated (small community, known experts)
  founding_pool:  all members (no scaling phase distinction)
  pilot risk:     low (everyone knows each other, social enforcement strong)

PROFILE 2 — Medium Fluid (150–400 members)
  dormains:       6–10
  circles:        5–8
  archetype_mix:  40% A, 30% B, 15% C, 8% D, 5% E, 2% others
  W_s_distribution: moderate spread (diverse expertise, some stars)
  founding_pool:  50–100 active members at bootstrap
  pilot risk:     medium (some unknown actors, coordination needed)

PROFILE 3 — Large Open (1000–3000 members)
  dormains:       10–20
  circles:        8–15
  archetype_mix:  30% A, 35% B, 15% C, 10% D, 5% E, 3% F, 2% others
  W_s_distribution: long tail (few high-W_s experts, large low-W_s base)
  founding_pool:  200–500 members at bootstrap
  pilot risk:     high (adversarial actors likely, coordination difficult)

PROFILE 4 — Adversarial Stress Test (any size, hostile environment)
  archetype_mix:  25% A, 15% B, 20% C, 20% D, 10% E, 5% F, 5% others
  purpose:        find the parameter regime where the system breaks
                  (not a realistic deployment profile — a worst-case)
```

---

## 4. Scenario Set

Ten scenarios covering routine operations, stress events, and adversarial
attack vectors.

---

### Scenario 1 — Normal Operations Baseline

**Purpose:** establish healthy system metrics under ideal conditions.

```
org_profile:      Profile 2
archetype_mix:    70% A, 30% B (no adversarial agents)
duration:         52 simulation cycles (1 cycle ≈ 1 week)
parameters:       all org defaults

measure:
  — W_s distribution shape over time (should spread and stratify)
  — motion throughput (motions filed per cycle, resolution rate)
  — aSTF revision_request rate (target: 10–25%)
  — participation breadth (% of members with ≥1 formal review per quarter)
  — novice progression rate (% of K=60 members reaching K=30 within 12 cycles)
  — burnout events (target: < 5% of active members per year)
```

**Success:** system reaches stable governance rhythm within 12 cycles.
No pathological W_s concentration (top 10% of members should not hold
> 40% of total W_s across all Dormains). aSTF revision rate in target range.

---

### Scenario 2 — Bootstrap Viability

**Purpose:** verify that the Step 3 vSTF self-verification mechanism works
across founding pool sizes and compositions.

```
founding_pool_sizes:  [10, 20, 30, 50, 100] members
W_h_submission_rates: [40%, 60%, 80%, 100%] of founding pool
dormain_count:        [3, 5, 8, 12]

measure:
  — does vSTF pool form successfully for each Dormain?
    (minimum 2 reviewers per claim required)
  — minimum founding pool size for successful bootstrap at 3 / 5 / 8 / 12 dormains
  — bootstrap duration (cycles from org creation to bootstrapped_at)
  — preliminary W_h accuracy (how close are preliminary values to verified values?)
```

**Key finding to extract:** the minimum viable founding pool size per
Dormain count. This becomes an Orb Sys onboarding recommendation:

```
Expected output (to be validated by simulation):
  3 dormains  → minimum ~15 members with W_h submissions
  5 dormains  → minimum ~25 members
  8 dormains  → minimum ~40 members
  12 dormains → minimum ~60 members
  (rough estimate — simulation will refine)
```

**Failure condition:** a Dormain has < 2 eligible reviewers for any pending
W_h claim. The simulation should surface the deadlock condition and the
parameter adjustment that resolves it (e.g. cross-Dormain reviewer eligibility
at reduced M_r,d weighting when primary Dormain reviewer pool is thin).

---

### Scenario 3 — Elite Closure Pressure

**Purpose:** verify the novice slot floor and curiosity-first matching
resist elite closure under realistic conditions.

```
org_profile:      Profile 2 or 3
archetype_mix:    40% A, 20% B, 30% C (Status Seekers), 10% D (Coalition Builders)
initial_condition: W_s highly concentrated in 15% of members (typical
                   of a community that was informally governed before PAAS)
duration:         52 cycles

measure:
  — novice xSTF participation rate over time
    (target: floor % or above sustained throughout)
  — W_s distribution Gini coefficient over time
    (should decrease as novices gain competence — inequality reducing)
  — new member → Circle member conversion rate
    (target: meaningful funnel, not blocked by elite gatekeeping)
  — K=60 → K=30 transition time for new members
    (should be faster with active novice slots than without)
```

**Compare:** run with novice_slot_floor_pct at [0%, 20%, 30%, 40%] and
measure the Gini coefficient trajectory. Identify the floor value at which
elite closure is effectively resisted without degrading decision quality
(low-competence novices in every STF slot degrades outcome quality).

---

### Scenario 4 — Coalition Capture Attempt

**Purpose:** verify that the anomaly detection and blind review isolation
prevent factional capture of the aSTF layer.

```
org_profile:      Profile 2
adversarial_agents: 2 Coalition Builder blocs (sizes 5 and 8)
                    operating independently with conflicting interests
duration:         30 cycles (focused stress test)

ATTACK SEQUENCE:
  Cycles 1–5:   Blocs establish W_s via mutual inflation (Archetypes D)
  Cycles 6–10:  Blocs attempt to dominate Circle membership via W_s
  Cycles 11–20: Blocs attempt to influence aSTF pool composition
                (nominating aligned members, discouraging rivals)
  Cycles 21–30: If undetected, attempt coordinated approval/rejection
                of specific motions

measure:
  — TYPE 2 anomaly detection latency (cycles until pattern flagged)
  — M_cmp freeze rate on coalition members once detected
  — Resolutions wrongly enacted before detection (false negatives)
  — Does the blind parallel structure delay coordination within blocs?
    (reviewers cannot see each other during aSTF — does this fragment
     the attack before all verdicts are filed?)
  — Post-detection: does the system self-repair or does the bloc
    find a new attack vector?
```

**Success condition:** anomaly detector fires within 8 cycles of coordinated
activity beginning. < 2 wrongly enacted Resolutions before detection.
M_cmp freeze prevents further coordinated vote weight amplification.

---

### Scenario 5 — Sybil Attack

**Purpose:** test proof-of-personhood and TYPE 3 anomaly detection against
coordinated fake identity clusters.

```
org_profile:      Profile 3 (large, harder to know everyone)
attack_size:      [5, 10, 20, 50] Sybil accounts per cluster
pop_config:       [none, email-only, vouching, VDC-backed]
attack_timing:    [immediate on joining, after 10 cycles of cover activity]

measure:
  — detection rate by cluster size and PoP configuration
  — time to detection (cycles)
  — maximum W_s achieved by cluster before detection
  — maximum vote weight concentration achieved before detection
  — false positive rate (legitimate members flagged as Sybil)
```

**Key finding:** the W_s value at which a Sybil cluster becomes governance-
threatening (able to control a majority of vote weight in any single Dormain).
If the detection mechanism catches the cluster well before this threshold,
the PoP requirement can remain relatively lightweight. If detection lags
behind the W_s growth curve, stronger PoP is warranted.

---

### Scenario 6 — Auditor Capture (Single and Coordinated)

**Purpose:** measure TYPE 2 anomaly detection performance against
captured aSTF reviewers at varying bias levels.

```
org_profile:      Profile 2
captured_auditors: [1, 2, 3] per scenario run
bias_magnitude:    [0.20, 0.35, 0.50, 0.70]
cover_rate:        [0.20, 0.40, 0.60]
blind_isolation:   enforced (tests how isolation slows coordination)

measure:
  — cycles to detection at each bias/cover combination
  — Resolutions wrongly decided before detection
  — Does coordinated capture (3 captured auditors) evade detection longer
    than single capture? (if yes: minimum aSTF pool size to dilute capture risk)
  — Does the composition balancer (biasing toward non-Coalition members for
    founding deliberation motions, §5b bootstrap doc) reduce capture risk
    for high-stakes motions?
```

**Output:** a detection reliability matrix — for each (bias_magnitude,
cover_rate) pair, what is the probability and latency of detection?
This informs the aSTF minimum pool size recommendation.

---

### Scenario 7 — Burnout Cascade

**Purpose:** test whether the Insight Engine guardrails prevent a burnout
cascade — a situation where key members burn out, load concentrates on
remaining members, triggering further burnout.

```
org_profile:      Profile 2
archetype_mix:    60% A, 40% G (Burnout Risk)
initial_condition: high participation demand (many open Cells, pending motions)
guardrail_config:  test with guardrails [ON / OFF]

measure:
  — burnout event frequency with and without guardrails
  — W_s concentration effect (does burnout of high-W_s members distort
    governance quality?)
  — system recovery time (cycles from cascade to stable participation)
  — critical threshold: at what % of high-W_s members burning out
    simultaneously does governance quality degrade below acceptable thresholds?
```

**Parameter to tune:** STF concurrent cap and notification frequency.
Identify the cap value that prevents cascade without artificially restricting
participation in healthy orgs.

---

### Scenario 8 — Non-System Resolution Accountability

**Purpose:** test that executing Circle assignment and Gate 2 interpretive
audit produce meaningful accountability for non-system resolutions.

```
org_profile:       Profile 2
resolution_types:  non-system directives only
executing_circles: varied (1 circle, 2 circles, 3 circles)
agent_types:       mixed A, B, C — execution quality varies by archetype
                   (A executes faithfully, B executes lazily, C may cherry-pick)

measure:
  — Gate 2 interpretive audit accuracy:
    does the aSTF correctly identify non-implementation, partial implementation,
    and faithful implementation?
  — False positive rate (faithful execution flagged as deviation)
  — False negative rate (non-implementation not caught)
  — Multi-circle execution: does one Circle's non-implementation
    affect the audit outcome for the other executing Circles?
  — Do executing Circles adjust behaviour when they know Gate 2 follows?
    (deterrence effect — measure implementation quality pre/post
    awareness that Gate 2 is enforced)
```

**Key design test:** verify that `implementing_circle_ids` being required
for non-system/hybrid motions (the correction noted before this document)
actually produces better accountability than leaving it optional.
Run with and without the requirement to measure the difference.

---

### Scenario 9 — Parameter Sensitivity Sweep

**Purpose:** systematic variation of core parameters to map the stable
operating regime and identify cliff edges.

```
PARAMETERS TO SWEEP (one at a time, holding others at default):

novice_slot_floor_pct:     [0.10, 0.20, 0.30, 0.40, 0.50]
rotation_window_max_weeks: [4, 8, 12, 16, 24]
delta_c_max (C_max):       [60, 90, 120, 150, 200]
delta_c_audit_trigger:     [25, 35, 50, 65, 80]
K_new:                     [40, 50, 60, 70, 80]
K_established:             [20, 25, 30, 35, 40]
K_veteran:                 [5, 8, 10, 15, 20]
composition_threshold:     [0.60, 0.70, 0.80, 0.90]
vote_concentration_threshold: [0.25, 0.33, 0.40, 0.50]
decay_half_life (default): [6, 9, 12, 18, 24 months]

for each parameter sweep:
  measure: governance quality index (composite — see §6)
           participation breadth
           W_s distribution Gini coefficient
           aSTF revision request rate
           detection rates for Scenarios 4–6
```

**Output:** for each parameter, identify the value range where the system
is robust (metrics stable) vs. the cliff edges where small changes produce
large degradation. Default parameter recommendations should sit in the
middle of the robust range, not near a cliff edge.

---

### Scenario 10 — Long-Run Stability (Generational)

**Purpose:** verify that the system does not ossify over time — that
new members can realistically gain meaningful W_s as founding members'
scores mature and K drops to 10.

```
org_profile:      Profile 2
duration:         260 cycles (≈ 5 years)
new_member_arrival: constant rate (5% of org size per year)
founding_member_activity: declining — 20% become inactive by cycle 100,
                           40% by cycle 200 (natural churn)

measure:
  — W_s distribution shape at cycles 52, 104, 156, 208, 260
  — new member → Circle member conversion rate over time
    (should remain stable — not declining as founding members mature)
  — does the decay mechanism prevent founding member W_s from
    becoming an insurmountable ceiling?
  — governance quality index trend (should not degrade as founding
    members' K drops to 10 and their scores stabilise)
  — Circle turnover rate (are Circles refreshing their membership
    or becoming permanent insider clubs?)
```

**Success:** at cycle 260, the org's governance quality is as good as
at cycle 52, and new members have realistic paths to meaningful influence.
The decay mechanism should be doing visible work — founding members who
stopped contributing should have lower W_s than newer active members
with equivalent expertise.

---

## 5. Parameter Sensitivity Ranges

Summary of parameters requiring simulation validation before
deployment recommendations can be made with confidence.

| Parameter | Default | Low Test | High Test | Risk if Too Low | Risk if Too High |
|---|---|---|---|---|---|
| `novice_slot_floor_pct` | 0.30 | 0.10 | 0.50 | Elite closure | Decision quality degradation |
| `rotation_window_max_weeks` | 12 | 4 | 24 | Burnout | Role entrenchment |
| `delta_c_max` (C_max) | 120 | 60 | 200 | Slow onboarding | Single-event W_s distortion |
| `delta_c_audit_trigger` | 50 | 25 | 80 | Undetected spikes | Audit overload |
| `K_new` | 60 | 40 | 80 | Slow new member growth | Volatile initial period |
| `K_veteran` | 10 | 5 | 20 | Over-stable veteran scores | Veteran W_s instability |
| `decay_half_life` (default) | 12 months | 6 months | 24 months | Knowledge relevance lag | Inactive member persistence |
| `decay_floor_pct` | 0.30 | 0.10 | 0.50 | Full erasure of history | Inactive members blocking newcomers |
| `composition_threshold` | 0.80 | 0.60 | 0.95 | Frequent false homogeneity flags | Genuine gaps missed |
| `vote_concentration_threshold` | 0.40 | 0.25 | 0.55 | Too many false concentration flags | Undetected plutocracy |
| `W_h_jstf_minimum` | (org-set) | — | — | jSTF lacks genuine expertise | Too few eligible members |
| `founding_min_pool_size` | TBD (Scenario 2) | — | — | Bootstrap deadlock | — |

---

## 6. Success & Failure Metrics

### Governance Quality Index (GQI)

A composite metric computed per simulation cycle:

```
GQI = weighted average of:

  participation_breadth       weight: 0.25
    — % of active members with ≥1 formal governance action in past 8 cycles
    target: > 60%

  decision_legitimacy         weight: 0.25
    — % of motions reaching resolution without Contested or Deadlock state
    target: > 80%

  oversight_effectiveness     weight: 0.20
    — aSTF revision_request rate in target range (10–25%)
    — TYPE 2/3 anomaly detection rate for seeded adversarial agents
    — false positive rate < 5%

  competence_mobility         weight: 0.15
    — new member → Circle member conversion within 26 cycles
    — Gini coefficient trend (should decline or remain stable)
    target: > 30% of active newcomers reaching Circle membership within 26 cycles

  system_stability            weight: 0.15
    — no undetected capture events
    — no Gate 2 Contested resolutions (diff failures)
    — burnout cascade events < 1 per 52 cycles

GQI range: 0–100
  > 80: healthy governance
  60–80: functional but watch signals
  40–60: parameter adjustment needed
  < 40: systemic failure — do not deploy at these parameters
```

---

### Specific Failure Conditions

```
HARD FAILURES (simulation should never reach these):
  — Sybil cluster controls > 50% vote weight in any Dormain before detection
  — Coalition capture produces > 5 wrongly enacted Resolutions
  — Bootstrap deadlock (Dormain with 0 eligible vSTF reviewers)
  — Burnout cascade leaves < 3 eligible aSTF reviewers in any active Dormain

SOFT FAILURES (require parameter adjustment, not deployment block):
  — Gini coefficient increasing after cycle 52 (inequality growing)
  — novice → Circle conversion rate < 15% in 26 cycles
  — aSTF revision_request rate > 40% (too many Cells compositionally weak)
  — aSTF revision_request rate < 5% (oversight rubber-stamping)
  — Founding bootstrap taking > 16 cycles in Profile 1 org (too slow)
```

---

## 7. Simulation Outputs

For each scenario run, produce:

```
PER-CYCLE TIME SERIES:
  — GQI and component scores
  — W_s distribution (mean, median, Gini, top-10% share)
  — Active member count by archetype
  — Motions filed / Resolutions enacted / Revision Requests issued
  — Anomaly flags triggered (type breakdown)
  — Burnout events
  — New member onboarding funnel progress

EVENT LOG (sampled):
  — All anomaly flags with cycle offset from seeded attack start
  — All Contested resolutions
  — All Bootstrap deadlock events
  — All hard failure events

PARAMETER SENSITIVITY HEAT MAPS:
  — GQI at each parameter sweep point
  — Detection rates at each adversarial scenario parameter combination
  — Minimum bootstrap pool size by Dormain count

FINAL REPORT PER SCENARIO:
  — Did the scenario succeed or fail against the target metrics?
  — Which parameters most influenced the outcome?
  — Recommended parameter adjustments from default
  — Confidence level (number of Monte Carlo runs, variance)
```

---

## 8. Known Fragility Points

Areas where the governance model is theoretically sound but empirically
untested. Simulation should pay particular attention to these.

**The preliminary W_h seeding problem (bootstrap).**
If the first members to register in Step 3 all have W_h in the same 1–2
Dormains, the vSTF cannot form for the remaining Dormains. The system
needs a minimum of 3 members with W_h in a Dormain to run a blind-parallel
vSTF (reviewer + subject isolation requires at least 2 reviewers who are
not the subject). Simulation Scenario 2 must find the minimum viable
founding composition by Dormain.

**The low-volume aSTF regime.**
In small orgs with few Dormain-competent members, the aSTF pool may be
thin enough that the blind parallel process (3 reviewers) cannot be formed
without drawing from a very small eligible population. This risks the pool
being predictable despite the sealing. Minimum aSTF pool size recommendation
should come from Scenario 6.

**The Revision Request loop.**
A pathological case: an aSTF issues a Revision Request, the Cell reactivates
and resubmits substantially unchanged, the next aSTF issues another Revision
Request. If this loops indefinitely, the motion is effectively stalled. The
simulation should test for this condition — what causes it, and does the
"ignored Revision Request is itself a signal" mechanism eventually produce
a Rejection rather than perpetual looping?

**Non-system resolution accountability without executing Circle.**
Scenario 8 directly tests this. The correction (requiring `implementing_circle_ids`
for non-system/hybrid motions) prevents the malformed case, but the simulation
should confirm that multi-circle executing assignments in hybrid motions do not
produce accountability diffusion — where each Circle assumes the other is
responsible and neither fully implements.

**The decay floor and zombie competence.**
The 0.3 × W_s_peak floor means a member who was highly active can retain
30% of their peak score indefinitely while contributing nothing. In a small
org where that member's peak W_s was very high, the floor may still leave
them with more vote weight than actively contributing newcomers. Scenario 10
long-run stability test should surface whether the floor creates a class
of permanently influential inactive members.

---

*Agent-Based Simulation Parameters v1.0 — compiled as final document in the
OrbSys implementation specification stack.*

*Document stack complete:*
- *OrbSys_v7.md — governance architecture*
- *OrbSys_engines_v2.md — engine trinity*
- *OrbSys_datamodel_v1.md — data model*
- *OrbSys_api_v1.md — API surface*
- *OrbSys_deployment_v1.md — deployment architecture*
- *OrbSys_bootstrap_v2.md — bootstrapping flow*
- *OrbSys_simulation_v1.md — agent-based simulation parameters*
