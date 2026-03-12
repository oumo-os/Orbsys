# Orb Sys — Data Model Sketch
## v1.0

> Entity-relationship model for the Orb Sys platform. Schema notation is
> PostgreSQL-flavoured for readability but the model is implementation-agnostic.
> Sealed fields, append-only tables, and isolation boundaries are noted explicitly.
>
> Cross-reference: OrbSys_v7.md, OrbSys_engines_v2.md

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Identity & Membership](#2-identity--membership)
3. [Competence Layer](#3-competence-layer)
4. [Organisation & Circles](#4-organisation--circles)
5. [Commons](#5-commons)
6. [Cells](#6-cells)
7. [Motions & Resolutions](#7-motions--resolutions)
8. [STF Instances](#8-stf-instances)
9. [Integrity Ledger](#9-integrity-ledger)
10. [Relationship Map](#10-relationship-map)
11. [Boundary & Access Notes](#11-boundary--access-notes)

---

## 1. Design Principles

**Append-only where it matters.**
The ledger, votes, verdicts, and competence events are append-only. Nothing is
updated in place — corrections are new rows that reference what they supersede.
All mutable application state (member state, resolution status, Cell state) lives
in separate tables that reference the ledger for their history.

**Sealed fields are structurally absent, not hidden.**
A sealed reviewer identity is not a NULL with a permission check on top. It is
literally not present in any queryable record until an unsealing event creates
a new ledger entry that contains it. Blind review isolation is not an access
control problem — it is a data model problem.

**Governance state is always derivable from the ledger.**
Current W_s, current Cell state, current member state — all can be reconstructed
from the ledger. The application layer maintains materialised views of current
state for performance, but the ledger is the source of truth.

**Dormains are org-specific.**
A Dormain is not a global taxonomy. Each org defines its own Dormains at setup.
The Inferential Engine's NLP classifier is trained on the org's defined Dormain
labels. Two orgs may have identically-named Dormains with different meanings.

---

## 2. Identity & Membership

### `members`

```sql
members (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  handle          TEXT NOT NULL,                   -- @handle within org
  display_name    TEXT NOT NULL,
  joined_at       TIMESTAMPTZ NOT NULL,
  current_state   TEXT NOT NULL                    -- materialised from ledger
                  CHECK (current_state IN (
                    'probationary','active','on_leave','inactive',
                    'under_review','suspended','exited'
                  )),
  proof_of_personhood_ref  TEXT,                   -- external VDC reference
  UNIQUE (org_id, handle)
)
```

**Notes:**
- `current_state` is a materialised view of the most recent
  `member_state_change` ledger event. The ledger holds the full history.
- `proof_of_personhood_ref` is an external reference to a Verifiable Digital
  Credential (VDC) used for Sybil defence. Not stored raw — referenced only.

---

### `member_exit_records`

```sql
member_exit_records (
  id              UUID PRIMARY KEY,
  member_id       UUID NOT NULL REFERENCES members(id),
  org_id          UUID NOT NULL REFERENCES orgs(id),
  circle_id       UUID REFERENCES circles(id),     -- null if org-level exit
  exit_state      TEXT NOT NULL
                  CHECK (exit_state IN (
                    -- voluntary
                    'resigned','forfeiture',
                    -- competence-driven
                    'competence_drift','credential_lapse',
                    -- process-driven
                    'rotation_end','audit_initiated_removal','transfer',
                    -- structural
                    'circle_reshuffle','circle_dissolution',
                    -- disciplinary
                    'judicial_penalty','org_expulsion'
                  )),
  exited_at       TIMESTAMPTZ NOT NULL,
  trigger_ref     UUID,                            -- ledger event that caused exit
  destination_circle_id UUID REFERENCES circles(id) -- for 'transfer' only
)
```

**Notes:**
- One row per exit event. A member can exit a Circle and later re-enter.
- Exit category grouping (voluntary / competence / process / structural /
  disciplinary) is derived from `exit_state` at query time, not stored.

---

### `curiosities`

```sql
curiosities (
  id              UUID PRIMARY KEY,
  member_id       UUID NOT NULL REFERENCES members(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  signal          NUMERIC(4,3) NOT NULL            -- 0.000 to 1.000
                  CHECK (signal >= 0 AND signal <= 1),
  declared_at     TIMESTAMPTZ NOT NULL,
  updated_at      TIMESTAMPTZ NOT NULL,
  UNIQUE (member_id, dormain_id)
)
```

**Notes:**
- Member updates this directly. No audit required — it is self-declared.
- Changes are NOT logged in the governance ledger (no governance consequence).
- Zero vote weight impact. Inferential Engine reads only.

---

## 3. Competence Layer

### `dormains`

```sql
dormains (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  name            TEXT NOT NULL,
  description     TEXT,
  parent_id       UUID REFERENCES dormains(id),    -- hierarchy (v1.1 feature)
  decay_fn        TEXT NOT NULL DEFAULT 'exponential',
  decay_half_life_months  NUMERIC(5,2) DEFAULT 12.0,
  decay_floor_pct NUMERIC(4,3) DEFAULT 0.300,      -- 0.3 × W_s_peak floor
  decay_config_resolution_id  UUID                 -- null = org default
                  REFERENCES resolutions(id),
  created_at      TIMESTAMPTZ NOT NULL,
  UNIQUE (org_id, name)
)
```

**Notes:**
- `parent_id` and transfer coefficients are stored but not computed in v1.0.
- `decay_fn`, `decay_half_life_months`, `decay_floor_pct` are governed params
  — updated only via enacted sys-bound Resolution (logged in ledger).
- `decay_config_resolution_id` is null until a Circle motion enacts a custom
  decay policy. Falls back to org-level defaults.

---

### `competence_scores`

Materialised current state. Source of truth is the ledger.

```sql
competence_scores (
  id              UUID PRIMARY KEY,
  member_id       UUID NOT NULL REFERENCES members(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  w_s             NUMERIC(7,2) NOT NULL DEFAULT 0,  -- soft competence, current
  w_s_peak        NUMERIC(7,2) NOT NULL DEFAULT 0,  -- highest W_s ever reached
  w_h             NUMERIC(7,2) NOT NULL DEFAULT 0,  -- hard competence (static)
  volatility_k    SMALLINT NOT NULL DEFAULT 60,
  proof_count     INTEGER NOT NULL DEFAULT 0,        -- formal review event count
  last_activity_at TIMESTAMPTZ,                      -- for decay calculation
  mcmp_status     TEXT NOT NULL DEFAULT 'active'
                  CHECK (mcmp_status IN ('active','frozen')),
  updated_at      TIMESTAMPTZ NOT NULL,
  UNIQUE (member_id, dormain_id)
)
```

**Notes:**
- `w_s` is updated by the Integrity Engine on each ΔC event.
- `w_s_peak` is used for the decay floor calculation (`0.3 × w_s_peak`).
- `mcmp_status = 'frozen'` suspends voting weight during investigation.
- Never written directly by application layer — only by the Integrity Engine
  processing a `delta_c_applied` ledger event.

---

### `delta_c_events`

Append-only. Every ΔC computation result.

```sql
delta_c_events (
  id              UUID PRIMARY KEY,
  member_id       UUID NOT NULL REFERENCES members(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  activity_id     UUID NOT NULL,                   -- ref to the source activity
  activity_type   TEXT NOT NULL
                  CHECK (activity_type IN (
                    'commons_formal_review',       -- G = 0.5
                    'cell_contribution_review',    -- G = 1.0
                    'motion_deliberation_review',  -- G = 1.0
                    'audit_formal_test',           -- G = 1.2
                    'vstf_credential_audit',       -- G = 1.2
                    'astf_period_review'           -- G = 1.2
                  )),
  gravity_g       NUMERIC(3,2) NOT NULL,
  volatility_k    SMALLINT NOT NULL,
  delta_raw       NUMERIC(8,2) NOT NULL,           -- before cap
  delta_applied   NUMERIC(8,2) NOT NULL,           -- after C_max = 120 cap
  ws_before       NUMERIC(7,2) NOT NULL,
  ws_after        NUMERIC(7,2) NOT NULL,
  status          TEXT NOT NULL DEFAULT 'applied'
                  CHECK (status IN ('applied','pending_audit','superseded')),
  superseded_by   UUID REFERENCES delta_c_events(id),
  computed_at     TIMESTAMPTZ NOT NULL
)
```

---

### `delta_c_reviewers`

The reviewer set `R` for each ΔC event. One row per reviewer.

```sql
delta_c_reviewers (
  id              UUID PRIMARY KEY,
  delta_c_event_id UUID NOT NULL REFERENCES delta_c_events(id),
  reviewer_id     UUID NOT NULL REFERENCES members(id),
  score_s         NUMERIC(4,3) NOT NULL            -- 0.000 to 1.000
                  CHECK (score_s >= 0 AND score_s <= 1),
  reviewer_w_d    NUMERIC(7,2) NOT NULL,           -- reviewer W_s in dormain at time of review
  circle_multiplier_m NUMERIC(3,2) NOT NULL        -- 1.0 / 1.2 / 1.6
                  CHECK (circle_multiplier_m IN (1.00, 1.20, 1.60)),
  provenance_note TEXT,                            -- optional in v1.0
  provenance_link TEXT,                            -- optional in v1.0
  reviewed_at     TIMESTAMPTZ NOT NULL
)
```

**Notes:**
- `reviewer_id` is always present here — this is the internal computation table,
  not the public governance record.
- In STF blind review contexts, the `reviewer_id` values in this table are not
  queryable via any public API endpoint until unsealing conditions are met.
  The Integrity Engine reads this table directly; no other service does.

---

### `wh_credentials`

```sql
wh_credentials (
  id              UUID PRIMARY KEY,
  member_id       UUID NOT NULL REFERENCES members(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  credential_type TEXT NOT NULL
                  CHECK (credential_type IN (
                    'degree','certification','patent','license',
                    'verified_external_contribution'
                  )),
  value_wh        NUMERIC(7,2) NOT NULL,
  vdc_reference   TEXT,                            -- Verifiable Digital Credential ref
  vstf_id         UUID REFERENCES stf_instances(id),
  resolution_id   UUID REFERENCES resolutions(id), -- the aSTF-approved motion
  verified_at     TIMESTAMPTZ NOT NULL,
  expires_at      TIMESTAMPTZ                      -- null = no expiry
)
```

---

## 4. Organisation & Circles

### `orgs`

```sql
orgs (
  id              UUID PRIMARY KEY,
  name            TEXT NOT NULL,
  slug            TEXT NOT NULL UNIQUE,
  purpose         TEXT,
  founding_tenets TEXT,                            -- free text, immutable after ratification
  commons_visibility TEXT NOT NULL DEFAULT 'members_only'
                  CHECK (commons_visibility IN (
                    'members_only','public','per_dormain'
                  )),
  created_at      TIMESTAMPTZ NOT NULL,
  bootstrapped_at TIMESTAMPTZ                      -- null until founding ratification complete
)
```

---

### `org_parameters`

Governed parameters. Updated only via enacted sys-bound Resolutions.

```sql
org_parameters (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  parameter       TEXT NOT NULL,
  value           JSONB NOT NULL,                  -- typed in application layer
  resolution_id   UUID REFERENCES resolutions(id),
  applied_at      TIMESTAMPTZ NOT NULL,
  UNIQUE (org_id, parameter)
)
```

Default parameter rows inserted at org creation:

| parameter | default value |
|---|---|
| `activity_gravity_informal` | `0.5` |
| `activity_gravity_formal` | `1.0` |
| `activity_gravity_audit` | `1.2` |
| `stf_rotation_window_min_weeks` | `2` |
| `stf_rotation_window_max_weeks` | `12` |
| `novice_slot_floor_pct` | `0.30` |
| `novice_ws_threshold` | `800` |
| `xstf_autoscale_threshold` | `10` |
| `composition_homogeneity_threshold` | `0.80` |
| `vote_weight_concentration_threshold` | `0.40` |
| `delta_c_max` | `120` |
| `delta_c_audit_trigger` | `50` |

---

### `circles`

```sql
circles (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  name            TEXT NOT NULL,
  description     TEXT,
  tenets          TEXT,
  is_suggested_starter  BOOLEAN NOT NULL DEFAULT false,
  created_at      TIMESTAMPTZ NOT NULL,
  dissolved_at    TIMESTAMPTZ,
  dissolution_resolution_id UUID REFERENCES resolutions(id),
  UNIQUE (org_id, name)
)
```

**Notes:**
- No `circle_type` enum. All Circles are the same object. `is_suggested_starter`
  is a UI hint only — it carries no system-level meaning.
- The Integrity Engine knows Circle mandate via `circle_dormains`, not via
  Circle name or type.

---

### `circle_dormains`

The mandate. What dormains a Circle is responsible for.

```sql
circle_dormains (
  id              UUID PRIMARY KEY,
  circle_id       UUID NOT NULL REFERENCES circles(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  mandate_type    TEXT NOT NULL DEFAULT 'primary'
                  CHECK (mandate_type IN ('primary','secondary')),
  -- primary = M = 1.6 for Circle members in this dormain
  -- secondary = M = 1.2
  added_at        TIMESTAMPTZ NOT NULL,
  removed_at      TIMESTAMPTZ,
  UNIQUE (circle_id, dormain_id)
)
```

---

### `circle_members`

```sql
circle_members (
  id              UUID PRIMARY KEY,
  circle_id       UUID NOT NULL REFERENCES circles(id),
  member_id       UUID NOT NULL REFERENCES members(id),
  joined_at       TIMESTAMPTZ NOT NULL,
  current_state   TEXT NOT NULL DEFAULT 'probationary'
                  CHECK (current_state IN (
                    'probationary','active','on_leave','inactive',
                    'under_review','suspended'
                  )),
  exited_at       TIMESTAMPTZ,
  exit_record_id  UUID REFERENCES member_exit_records(id)
)
```

---

### `circle_health_snapshots`

Produced after each periodic aSTF cycle. Not computed continuously.

```sql
circle_health_snapshots (
  id              UUID PRIMARY KEY,
  circle_id       UUID NOT NULL REFERENCES circles(id),
  astf_instance_id UUID NOT NULL REFERENCES stf_instances(id),
  cycle_end       TIMESTAMPTZ NOT NULL,
  mandate_adherence_score  NUMERIC(5,2),           -- 0–100, from aSTF checklist aggregate
  activity_score           NUMERIC(5,2),
  decision_quality_score   NUMERIC(5,2),           -- Gate 1 aSTF approval rate
  areas_of_concern         TEXT[],
  created_at      TIMESTAMPTZ NOT NULL
)
```

---

## 5. Commons

### `commons_threads`

```sql
commons_threads (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  author_id       UUID NOT NULL REFERENCES members(id),
  title           TEXT NOT NULL,
  body            TEXT NOT NULL,
  visibility      TEXT NOT NULL DEFAULT 'inherited'
                  CHECK (visibility IN ('inherited','public','members_only')),
  -- 'inherited' = use org-level commons_visibility setting
  state           TEXT NOT NULL DEFAULT 'open'
                  CHECK (state IN ('open','frozen','archived')),
  freeze_reason   TEXT                             -- null if not frozen
                  CHECK (freeze_reason IN (
                    NULL,'conduct','judicial','policy'
                  )),
  freeze_ref      UUID,                            -- ledger event ref
  sponsored_at    TIMESTAMPTZ,                     -- null until sponsored
  sponsoring_cell_id UUID REFERENCES cells(id),    -- null until sponsored
  created_at      TIMESTAMPTZ NOT NULL
)
```

---

### `commons_thread_dormain_tags`

```sql
commons_thread_dormain_tags (
  id              UUID PRIMARY KEY,
  thread_id       UUID NOT NULL REFERENCES commons_threads(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  source          TEXT NOT NULL
                  CHECK (source IN ('author','inferential_engine','human_correction')),
  tagged_by       UUID REFERENCES members(id),     -- null if inferential_engine
  tagged_at       TIMESTAMPTZ NOT NULL,
  corrected_from_dormain_id UUID REFERENCES dormains(id), -- for human_correction rows
  UNIQUE (thread_id, dormain_id)
)
```

---

### `commons_posts`

```sql
commons_posts (
  id              UUID PRIMARY KEY,
  thread_id       UUID NOT NULL REFERENCES commons_threads(id),
  author_id       UUID NOT NULL REFERENCES members(id),
  body            TEXT NOT NULL,
  parent_post_id  UUID REFERENCES commons_posts(id), -- threaded replies
  created_at      TIMESTAMPTZ NOT NULL,
  edited_at       TIMESTAMPTZ
  -- no delete; edits create a new version flagged in the ledger
)
```

---

### `commons_formal_reviews`

When a Circle member formally reviews a Commons post (triggers ΔC).

```sql
commons_formal_reviews (
  id              UUID PRIMARY KEY,
  post_id         UUID NOT NULL REFERENCES commons_posts(id),
  reviewer_id     UUID NOT NULL REFERENCES members(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  score_s         NUMERIC(4,3) NOT NULL
                  CHECK (score_s >= 0 AND score_s <= 1),
  delta_c_event_id UUID REFERENCES delta_c_events(id), -- null until computed
  reviewed_at     TIMESTAMPTZ NOT NULL,
  UNIQUE (post_id, reviewer_id, dormain_id)
)
```

---

## 6. Cells

### `cells`

```sql
cells (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  cell_type       TEXT NOT NULL
                  CHECK (cell_type IN (
                    'deliberation',
                    'closed_circle',
                    'motion_review',           -- aSTF Gate 1 sub-cell
                    'stf_workspace',           -- xSTF, jSTF, Meta-aSTF
                    'periodic_audit'           -- periodic aSTF
                  )),
  visibility      TEXT NOT NULL DEFAULT 'closed'
                  CHECK (visibility IN ('open','closed')),
  -- open: invited circles write; all org members read
  -- closed: invited circles only
  state           TEXT NOT NULL DEFAULT 'active'
                  CHECK (state IN (
                    'active','temporarily_closed','reactivated',
                    'archived','dissolved','frozen','suspended'
                  )),
  initiating_member_id  UUID NOT NULL REFERENCES members(id),
  parent_cell_id        UUID REFERENCES cells(id), -- for motion_review sub-cells
  commons_thread_id     UUID REFERENCES commons_threads(id),
  commons_snapshot_at   TIMESTAMPTZ,               -- moment of sponsorship snapshot
  stf_instance_id       UUID REFERENCES stf_instances(id),
  founding_mandate      TEXT,                      -- Insight Engine draft at sponsorship
  created_at            TIMESTAMPTZ NOT NULL,
  state_changed_at      TIMESTAMPTZ NOT NULL
)
```

---

### `cell_invited_circles`

```sql
cell_invited_circles (
  id              UUID PRIMARY KEY,
  cell_id         UUID NOT NULL REFERENCES cells(id),
  circle_id       UUID NOT NULL REFERENCES circles(id),
  invited_because TEXT NOT NULL
                  CHECK (invited_because IN (
                    'dormain_mandate','initiating_circle','revision_directive'
                  )),
  invited_at      TIMESTAMPTZ NOT NULL,
  routing_dormain_ids  UUID[],                     -- which dormains drove the invite
  UNIQUE (cell_id, circle_id)
)
```

---

### `cell_contributions`

The raw Cell record. Append-only within the Cell's active period.

```sql
cell_contributions (
  id              UUID PRIMARY KEY,
  cell_id         UUID NOT NULL REFERENCES cells(id),
  author_id       UUID NOT NULL REFERENCES members(id),
  body            TEXT NOT NULL,
  contribution_type TEXT NOT NULL DEFAULT 'discussion'
                  CHECK (contribution_type IN (
                    'discussion',
                    'commons_context_import', -- member bringing in Commons context
                    'revision_directive_response',
                    'evidence_attachment'
                  )),
  commons_post_ref UUID REFERENCES commons_posts(id), -- for commons_context_import
  created_at      TIMESTAMPTZ NOT NULL
)
```

**Notes:**
- `commons_context_import` is how Cell members bring Commons thread context into
  the Cell explicitly (see engines v2 §2b). The Commons post is referenced; the
  member is the accountable actor who judged it relevant.

---

### `cell_composition_profiles`

Computed by the Integrity Engine on demand when an aSTF pool is being constituted.

```sql
cell_composition_profiles (
  id              UUID PRIMARY KEY,
  cell_id         UUID NOT NULL REFERENCES cells(id),
  computed_at     TIMESTAMPTZ NOT NULL,
  profile         JSONB NOT NULL
  -- structure:
  -- {
  --   "dormain_weights": {
  --     "<dormain_id>": {
  --       "weighted_contribution": 847.3,
  --       "pct_of_total": 0.34,
  --       "target_pct": 0.40,
  --       "gap": 0.06
  --     },
  --     ...
  --   },
  --   "total_contribution_weight": 2491.0,
  --   "gap_dormains": ["<dormain_id_with_highest_gap>", ...]
  -- }
)
```

---

### `cell_votes`

Competence-weighted votes on motions. Append-only.

```sql
cell_votes (
  id              UUID PRIMARY KEY,
  cell_id         UUID NOT NULL REFERENCES cells(id),
  motion_id       UUID NOT NULL REFERENCES motions(id),
  voter_id        UUID NOT NULL REFERENCES members(id),
  dormain_id      UUID NOT NULL REFERENCES dormains(id),
  vote            TEXT NOT NULL CHECK (vote IN ('yea','nay','abstain')),
  w_s_at_vote     NUMERIC(7,2) NOT NULL,           -- voter's W_s at time of vote
  weight          NUMERIC(9,2) NOT NULL,            -- effective vote weight
  voted_at        TIMESTAMPTZ NOT NULL,
  UNIQUE (motion_id, voter_id, dormain_id)
)
```

---

## 7. Motions & Resolutions

### `motions`

```sql
motions (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  cell_id         UUID NOT NULL REFERENCES cells(id),
  motion_type     TEXT NOT NULL
                  CHECK (motion_type IN ('sys_bound','non_system','hybrid')),
  state           TEXT NOT NULL DEFAULT 'draft'
                  CHECK (state IN (
                    'draft','active','voted',
                    'gate1_pending','gate1_approved','gate1_rejected',
                    'revision_requested',          -- new verdict type
                    'pending_implementation',
                    'gate2_pending','enacted','enacted_locked',
                    'contested','deviated_justified','abandoned'
                  )),
  filed_by        UUID NOT NULL REFERENCES members(id),
  insight_draft_ref UUID,                          -- ref to the Insight Engine draft used
  created_at      TIMESTAMPTZ NOT NULL,
  crystallised_at TIMESTAMPTZ,
  state_changed_at TIMESTAMPTZ NOT NULL
)
```

---

### `motion_directives`

Non-system and hybrid motions carry a text directive.

```sql
motion_directives (
  id              UUID PRIMARY KEY,
  motion_id       UUID NOT NULL UNIQUE REFERENCES motions(id),
  body            TEXT NOT NULL,
  commitments     TEXT[],                          -- extracted by Insight Engine, confirmed by member
  ambiguities_flagged TEXT[]                       -- open questions flagged before filing
)
```

---

### `motion_specifications`

System-bound and hybrid motions carry a structured specification block.

```sql
motion_specifications (
  id              UUID PRIMARY KEY,
  motion_id       UUID NOT NULL REFERENCES motions(id),
  parameter       TEXT NOT NULL,
  new_value       JSONB NOT NULL,
  justification   TEXT NOT NULL,
  pre_validation_status TEXT NOT NULL DEFAULT 'pending'
                  CHECK (pre_validation_status IN (
                    'pending','valid','invalid_range',
                    'invalid_parameter','missing_justification'
                  )),
  pre_validated_at TIMESTAMPTZ
)
```

**Notes:**
- One row per parameter in the specification block.
- Pre-validation by the Integrity Engine runs before Gate 1 opens.
  An invalid specification is returned to the Cell for correction without
  consuming an aSTF assignment.
- All rows in the specification block must have `pre_validation_status = 'valid'`
  before Gate 1 can open.

---

### `resolutions`

```sql
resolutions (
  id              UUID PRIMARY KEY,
  motion_id       UUID NOT NULL UNIQUE REFERENCES motions(id),
  org_id          UUID NOT NULL REFERENCES orgs(id),
  resolution_ref  TEXT NOT NULL UNIQUE,            -- e.g. 'ORG-2024-011'
  state           TEXT NOT NULL DEFAULT 'pending_implementation'
                  CHECK (state IN (
                    'pending_implementation','gate2_pending',
                    'enacted','enacted_locked','contested',
                    'deviated_justified','deviated_unjustified'
                  )),
  implementation_type TEXT NOT NULL
                  CHECK (implementation_type IN (
                    'sys_parameter','identity_change','competence_adjustment',
                    'disciplinary','org_bound'
                  )),
  implementing_circle_id UUID REFERENCES circles(id), -- null for sys_parameter (Integrity Engine)
  gate2_agent     TEXT NOT NULL
                  CHECK (gate2_agent IN ('astf_diff','astf_interpretive','vstf','jstf')),
  enacted_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL
)
```

---

### `resolution_gate2_diffs`

For sys-bound resolutions — the Integrity Engine's diff result.

```sql
resolution_gate2_diffs (
  id              UUID PRIMARY KEY,
  resolution_id   UUID NOT NULL REFERENCES resolutions(id),
  parameter       TEXT NOT NULL,
  specified_value JSONB NOT NULL,
  applied_value   JSONB,                           -- null if write failed
  match           BOOLEAN NOT NULL,
  checked_at      TIMESTAMPTZ NOT NULL
)
```

---

## 8. STF Instances

### `stf_instances`

```sql
stf_instances (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  stf_type        TEXT NOT NULL
                  CHECK (stf_type IN (
                    'xstf','astf_motion','astf_periodic',
                    'vstf','jstf','meta_astf'
                  )),
  state           TEXT NOT NULL DEFAULT 'forming'
                  CHECK (state IN (
                    'forming','active','all_filed',
                    'completed','dissolved'
                  )),
  mandate         TEXT NOT NULL,
  commissioned_by_circle_id UUID REFERENCES circles(id),
  parent_stf_id   UUID REFERENCES stf_instances(id), -- jSTF → Meta-aSTF
  cell_id         UUID REFERENCES cells(id),
  motion_id       UUID REFERENCES motions(id),      -- for astf_motion
  resolution_id   UUID REFERENCES resolutions(id),  -- for gate2 astfs
  subject_member_id UUID REFERENCES members(id),    -- for vstf, jstf
  composition_profile_id UUID REFERENCES cell_composition_profiles(id),
  deadline        TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL,
  completed_at    TIMESTAMPTZ
)
```

---

### `stf_assignments`

```sql
stf_assignments (
  id              UUID PRIMARY KEY,
  stf_instance_id UUID NOT NULL REFERENCES stf_instances(id),
  member_id       UUID NOT NULL REFERENCES members(id),
  slot_type       TEXT NOT NULL DEFAULT 'standard'
                  CHECK (slot_type IN ('standard','novice_reserved')),
  assigned_at     TIMESTAMPTZ NOT NULL,
  rotation_end    TIMESTAMPTZ,
  -- Blind review fields — only populated for astf_motion, vstf, astf_periodic
  isolated_view_token TEXT UNIQUE,                 -- opaque token per reviewer
  -- This token is the only way the reviewer accesses their isolated view.
  -- It does not reveal their identity or the identity of other reviewers.
  verdict_filed_at TIMESTAMPTZ                     -- null until filed
)
```

---

### `stf_verdicts`

Append-only. One row per filed verdict.

```sql
stf_verdicts (
  id              UUID PRIMARY KEY,
  stf_instance_id UUID NOT NULL REFERENCES stf_instances(id),
  assignment_id   UUID NOT NULL UNIQUE REFERENCES stf_assignments(id),
  -- reviewer_id is NOT stored here in the primary record.
  -- It exists only in stf_assignments and is queryable only after unsealing.
  verdict         TEXT NOT NULL
                  CHECK (verdict IN (
                    'approve','reject','revision_request',  -- aSTF motion
                    'clear','concerns','violation',          -- periodic aSTF dimensions
                    'adequate','insufficient',               -- vSTF
                    'finding_confirmed','finding_rejected'   -- jSTF / meta
                  )),
  rationale       TEXT,
  revision_directive TEXT,                         -- populated for 'revision_request' verdicts
  checklist       JSONB,                           -- for periodic aSTF multi-dimension results
  -- {
  --   "mandate_adherence": "clear|concerns|violation",
  --   "activity":          "clear|concerns|violation",
  --   "decision_quality":  "clear|concerns|violation",
  --   "notes": "..."
  -- }
  filed_at        TIMESTAMPTZ NOT NULL
)
```

**Notes:**
- `reviewer_id` is intentionally absent from this table. The mapping from verdict
  to reviewer identity exists only in `stf_assignments.member_id`.
- `stf_assignments.member_id` is not exposed via any API endpoint until an
  unsealing event is logged in the ledger.
- The aggregation query that derives the STF outcome joins `stf_verdicts` to
  `stf_assignments` — but this join is only permitted to the Integrity Engine
  process that runs aggregation, not to any application-layer query.

---

### `stf_unsealing_events`

Created only when an unsealing condition is met (malpractice or judicial penalty).

```sql
stf_unsealing_events (
  id              UUID PRIMARY KEY,
  stf_instance_id UUID NOT NULL REFERENCES stf_instances(id),
  assignment_id   UUID NOT NULL REFERENCES stf_assignments(id),
  unsealing_condition TEXT NOT NULL
                  CHECK (unsealing_condition IN (
                    'malpractice_finding','judicial_penalty'
                  )),
  triggered_by_ruling_id UUID NOT NULL,            -- resolution_id or stf_instance_id
  unsealed_at     TIMESTAMPTZ NOT NULL
)
```

After an unsealing event is created, the member identity for that assignment
becomes queryable via `stf_assignments.member_id` — not before.

---

## 9. Integrity Ledger

The ledger is the source of truth for all governance state. Every row is
append-only. The `supersedes` field links correction entries to the entries
they correct.

### `ledger_events`

```sql
ledger_events (
  id              UUID PRIMARY KEY,
  org_id          UUID NOT NULL REFERENCES orgs(id),
  event_type      TEXT NOT NULL,                   -- see full taxonomy below
  subject_id      UUID,                            -- primary entity affected
  subject_type    TEXT,
  payload         JSONB NOT NULL,                  -- event-specific data
  supersedes      UUID REFERENCES ledger_events(id),
  triggered_by_member UUID REFERENCES members(id), -- null for engine-triggered events
  triggered_by_resolution UUID REFERENCES resolutions(id),
  created_at      TIMESTAMPTZ NOT NULL,
  -- cryptographic integrity
  prev_hash       TEXT NOT NULL,                   -- hash of previous event in chain
  event_hash      TEXT NOT NULL UNIQUE             -- SHA-256 of (id + payload + prev_hash)
)
```

**Event type taxonomy:**

```
governance:
  cell_created              cell_state_changed        cell_dissolved
  cell_archived             cell_composition_computed
  thread_created            thread_sponsored          thread_frozen
  thread_unfrozen           thread_dormain_tagged      thread_tag_corrected
  motion_filed              motion_state_changed
  vote_cast                 vote_weight_computed
  stf_verdict_filed         stf_aggregation_complete  stf_identity_unsealed
  revision_request_issued
  resolution_created        resolution_state_changed
  system_parameter_changed  org_parameter_changed

competence:
  delta_c_applied           delta_c_pending_audit     delta_c_correction
  competence_decay_applied  wh_verified               wh_boost_applied
  volatility_k_updated

oversight:
  anomaly_flagged           anomaly_resolved
  mcmp_frozen               mcmp_restored
  member_state_changed      member_exited

structural:
  circle_created            circle_dissolved          circle_member_added
  circle_member_state_changed  circle_dormain_added   circle_dormain_removed
  org_created               org_parameter_changed     dormain_created
  dormain_decay_policy_changed
```

---

### Cryptographic Chain

Each event carries `prev_hash` (hash of the immediately preceding event) and
`event_hash` (SHA-256 of `id + payload + prev_hash`). This creates a hash chain
across all events in an org's ledger — any tampering with a historical event
invalidates all subsequent hashes.

```
event_hash(n) = SHA-256(
  event_id(n) ||
  payload_json(n) ||
  prev_hash(n)          -- = event_hash(n-1)
)
```

The chain can be verified independently by any party with read access to the
ledger — no trusted third party required for audit.

---

## 10. Relationship Map

```
org
 ├── dormains (org-specific)
 │     └── decay policy (governed param, Circle motion)
 ├── circles
 │     ├── circle_dormains → dormains (mandate)
 │     └── circle_members → members
 ├── members
 │     ├── competence_scores → dormains
 │     ├── delta_c_events → dormains, activities
 │     ├── curiosities → dormains
 │     └── wh_credentials → dormains
 ├── commons
 │     ├── commons_threads
 │     │     ├── dormain_tags → dormains (3-layer)
 │     │     └── commons_posts
 │     │           └── commons_formal_reviews → delta_c_events
 │     └── [thread → sponsored → cell]
 ├── cells
 │     ├── cell_invited_circles → circles
 │     ├── cell_contributions (append-only, member-attributed)
 │     ├── cell_composition_profiles (on-demand, Integrity Engine)
 │     ├── cell_votes → motions
 │     └── [parent cell ← motion_review sub-cell]
 ├── motions
 │     ├── motion_directives (non-system, hybrid)
 │     ├── motion_specifications (sys-bound, hybrid)
 │     └── → resolutions
 ├── resolutions
 │     ├── resolution_gate2_diffs (sys-bound)
 │     └── → [sys writes via Integrity Engine]
 ├── stf_instances
 │     ├── stf_assignments → members (identity sealed in blind types)
 │     ├── stf_verdicts (reviewer_id absent)
 │     └── stf_unsealing_events (two conditions only)
 └── ledger_events (append-only, cryptographic chain)
       └── [all of the above emit events here]
```

---

## 11. Boundary & Access Notes

### Engine access boundaries

| Table / Query | Inferential Engine | Insight Engine | Integrity Engine | Application Layer |
|---|---|---|---|---|
| `competence_scores` | Read | Read | Read + Write | Read |
| `curiosities` | Read | — | — | Read + Write (member only) |
| `cell_composition_profiles` | Read (receives signal) | — | Read + Write | Read |
| `delta_c_reviewers` | — | — | Read + Write | **No access** |
| `stf_assignments.member_id` (blind types) | — | — | Read (aggregation only) | **No access until unsealing** |
| `stf_verdicts` | — | — | Read + Write | Read (after aggregation) |
| `cell_contributions` (blind review cells) | — | — | Read | **No access** |
| `ledger_events` | Read | Read | Write | Read |
| `org_parameters` | Read | Read | Read + Write | Read |

### Isolation boundary for blind review Cells

A `motion_review` or `astf_periodic` Cell has a hard isolation model:

```
Each reviewer r has an isolated_view_token (stf_assignments.isolated_view_token).

Permitted via token:
  — Read: motion text, deliberation cell record, commons snapshot
  — Write: own stf_verdicts row only

Blocked (no endpoint exists, not just access-controlled):
  — Reviewer list for this STF
  — Other reviewers' tokens or assignment rows
  — Other reviewers' verdict rows (before aggregation)
  — Cell contribution feed of any other reviewer's isolated view

After all_verdicts_filed:
  — Aggregation runs in Integrity Engine
  — Result published to org archive
  — Reviewer identities remain sealed (stf_unsealing_events required to expose)
```

### Append-only enforcement

The following tables must be enforced as insert-only at the database layer
(trigger or policy — not just application convention):

```
ledger_events
delta_c_events
delta_c_reviewers
cell_contributions
cell_votes
stf_verdicts
stf_unsealing_events
commons_posts
```

Corrections to these records are new rows with `supersedes` populated,
not updates to existing rows.

---

*Data Model v1.0 — compiled alongside OrbSys_v7.md and OrbSys_engines_v2.md.*
*Next: API surface sketch — endpoints, auth model, event emission.*
