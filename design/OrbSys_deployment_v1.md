# Orb Sys — Deployment Architecture
## v1.0

> Service topology, infrastructure layout, ledger backend options, and
> multi-org tenancy model.
>
> Cross-reference: OrbSys_api_v1.md, OrbSys_datamodel_v1.md,
> OrbSys_engines_v2.md

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Service Map](#2-service-map)
3. [Database Layer](#3-database-layer)
4. [Event Bus](#4-event-bus)
5. [Engine Deployment Model](#5-engine-deployment-model)
6. [Ledger Backend Options](#6-ledger-backend-options)
7. [Multi-Org Tenancy Model](#7-multi-org-tenancy-model)
8. [Infrastructure Topology](#8-infrastructure-topology)
9. [Deployment Tiers](#9-deployment-tiers)
10. [Failure Modes & Recovery](#10-failure-modes--recovery)

---

## 1. Design Principles

**Isolation is structural, not just configured.**
The Integrity Engine's exclusive write access to governed tables is enforced
at the database connection level — a different DB role with different grants,
not just application-layer convention. The blind review join restriction is
enforced the same way. If the application API server were compromised,
it still could not write competence scores or read sealed reviewer identities.

**The engines are consumers, not servers.**
All three engines run as event-driven consumers off the event bus. They do
not serve public traffic. The API server talks to engines only via internal
RPC on isolated network segments — and only for the synchronous on-demand
calls (draft proposal, motion draft, dormain tagging). Everything else is
async via the bus.

**The Integrity Engine is single-writer per org.**
The hash chain on the ledger requires ordered, serialised writes. A single
Integrity Engine process owns writes for a given org. This is not a
performance bottleneck in practice — governance events are low-frequency
relative to typical database write loads. Horizontal read scaling is
independent of this constraint.

**LLM capability is a pluggable dependency.**
The Insight Engine's summarisation and drafting functions require language
model inference. In v1.0, this is an external call (configurable provider
— self-hosted or API). The engine interface does not change based on which
backend is used. Orgs can choose their inference tier based on privacy
requirements and cost tolerance.

---

## 2. Service Map

```
                         ┌─────────────────────────────────┐
                         │         PUBLIC INTERNET          │
                         └──────────────┬──────────────────┘
                                        │ HTTPS
                         ┌──────────────▼──────────────────┐
                         │          API GATEWAY             │
                         │   TLS termination, rate limit,   │
                         │   token type routing             │
                         └──────┬──────────────────┬───────┘
                                │                  │
                    ┌───────────▼────┐   ┌─────────▼───────────┐
                    │   API SERVER   │   │   BLIND REVIEW API   │
                    │  (member-facing│   │  (isolated_view_token│
                    │   endpoints)   │   │   endpoints only)    │
                    └───────┬────────┘   └─────────┬───────────┘
                            │                      │
                   internal RPC             internal RPC
                   (sync, on-demand)        (isolated DB role)
                            │                      │
         ┌──────────────────┼──────────────────────┤
         │                  │                      │
┌────────▼──────┐  ┌────────▼──────┐  ┌───────────▼───────────┐
│  INFERENTIAL  │  │    INSIGHT    │  │      INTEGRITY         │
│    ENGINE     │  │    ENGINE     │  │       ENGINE           │
│               │  │               │  │                        │
│  NLP/vector   │  │  LLM (summ.   │  │  Hash chain writer     │
│  matching     │  │  + drafting)  │  │  ΔC computation        │
│  tagging      │  │  scheduling   │  │  Anomaly detection     │
│               │  │  notifications│  │  System writes         │
└───────┬───────┘  └───────┬───────┘  └───────────┬───────────┘
        │                  │                       │
        └──────────────────┴───────────────────────┘
                           │
              ┌────────────▼─────────────┐
              │         EVENT BUS        │
              │   (durable, ordered,     │
              │    per-org partitioned)  │
              └────────────┬─────────────┘
                           │
              ┌────────────▼─────────────┐
              │       DATABASE LAYER     │
              │                         │
              │  App DB (PostgreSQL)    │
              │  Ledger store           │
              │  LLM inference backend  │
              │  Object store (files,   │
              │   snapshots, reports)   │
              └─────────────────────────┘
```

---

## 3. Database Layer

### Application Database

PostgreSQL. The primary store for all mutable application state and the
append-only governance tables.

**Database roles — enforced at connection level:**

```
role: app_rw
  grants:
    SELECT, INSERT on: all tables
    UPDATE on: members, circle_members (state fields only),
               cells (state fields only), motions (state fields only),
               competence_scores (updated_at only — w_s via integrity_rw)
    No UPDATE on: ledger_events, delta_c_events, cell_votes,
                  stf_verdicts, commons_posts (append-only tables)
  used by: API server

role: blind_review_rw
  grants:
    SELECT on: motions, cell_contributions (deliberation cells only),
               commons_threads, commons_posts (pre-snapshot only)
    INSERT on: stf_verdicts
    No SELECT on: stf_assignments.member_id (blind type instances)
    No SELECT on: stf_verdicts (pre-aggregation, own row excepted)
  used by: Blind Review API server

role: integrity_rw
  grants:
    SELECT on: all tables
    INSERT on: ledger_events, delta_c_events, delta_c_reviewers,
               cell_composition_profiles, stf_unsealing_events,
               resolution_gate2_diffs
    UPDATE on: competence_scores (all fields),
               org_parameters (value, applied_at),
               dormains (decay fields),
               stf_instances (state, completed_at),
               stf_assignments (verdict_filed_at),
               motions (state, state_changed_at),
               resolutions (state, enacted_at)
    SELECT on: stf_assignments.member_id (ALL instances including blind)
  used by: Integrity Engine ONLY

role: inferential_ro
  grants:
    SELECT on: competence_scores, curiosities, dormains, circle_dormains,
               cell_composition_profiles, commons_thread_dormain_tags,
               org_parameters, circles, circle_members
    No access to: stf_assignments, stf_verdicts, delta_c_reviewers,
                  cell_contributions (blind cells), ledger_events (internal)
  used by: Inferential Engine

role: insight_ro
  grants:
    SELECT on: cell_contributions (non-blind cells only), commons_threads,
               commons_posts, motions, motion_directives, ledger_events,
               resolutions, cells, org_parameters, members (public fields)
    No access to: cell_contributions (blind review cells),
                  stf_assignments, stf_verdicts, delta_c_reviewers
  used by: Insight Engine
```

**Append-only enforcement — database triggers:**

```sql
-- Applied to all append-only tables
CREATE OR REPLACE FUNCTION enforce_append_only()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Table % is append-only. Updates and deletes are prohibited.',
    TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

-- Applied to: ledger_events, delta_c_events, delta_c_reviewers,
--   cell_contributions, cell_votes, stf_verdicts, stf_unsealing_events,
--   commons_posts, delta_c_reviewers
CREATE TRIGGER enforce_append_only_trigger
  BEFORE UPDATE OR DELETE ON <table>
  FOR EACH ROW EXECUTE FUNCTION enforce_append_only();
```

This is a database-level guarantee — not application convention. Even a direct
psql session with the wrong role cannot modify these rows.

---

### Row-Level Security for Blind Review

For the `cell_contributions` table, RLS enforces that the `insight_ro` role
cannot read from blind review Cells:

```sql
ALTER TABLE cell_contributions ENABLE ROW LEVEL SECURITY;

CREATE POLICY insight_no_blind_cells ON cell_contributions
  FOR SELECT TO insight_ro
  USING (
    cell_id NOT IN (
      SELECT id FROM cells
      WHERE cell_type IN ('motion_review','periodic_audit')
    )
  );
```

The Inferential Engine has no access to `cell_contributions` at all.
The Integrity Engine (`integrity_rw`) bypasses RLS for aggregation.

---

## 4. Event Bus

### Requirements

- **Durable** — events must survive broker restart without loss
- **Ordered** — per-org, per-subject ordering matters for the hash chain
- **Replayable** — engines must be able to replay from a checkpoint on restart
- **Per-org partitioned** — org A's events never enter org B's processing

### Recommended: NATS JetStream

NATS JetStream provides durable, ordered, replayable streams with low
operational overhead. It fits the event volume profile of governance
(low-to-medium frequency, high semantic importance) better than Kafka,
which is optimised for high-throughput use cases.

```
Stream per org:   ORG.<org_id>.events
Subject routing:  ORG.<org_id>.<event_type>

Consumer groups:
  inferential.consumer    — subscribes to: thread_created, thread_tag_corrected,
                            cell_created, stf_commissioned, motion_filed
  insight.consumer        — subscribes to: cell_created, cell_contribution_batch,
                            motion_filed, resolution_state_changed,
                            stf_deadline_approaching, anomaly_flagged
  integrity.consumer      — subscribes to: ALL events (primary processor)
  notification.consumer   — subscribes to: all events that trigger member
                            notifications (driven by Insight Engine output)
```

### Message format

```json
{
  "id":          "<uuid>",
  "org_id":      "<uuid>",
  "event_type":  "vote_cast",
  "subject_id":  "<uuid>",
  "subject_type": "motion",
  "payload":     { ... },
  "emitted_by":  "<service_name>",
  "emitted_at":  "<iso8601>",
  "ledger_event_id": "<uuid>"   // set after Integrity Engine writes to ledger
}
```

`ledger_event_id` is null when first emitted by the API server. The Integrity
Engine writes to the ledger and re-emits the event with the `ledger_event_id`
populated. Other engine consumers wait for the re-emitted version (with
ledger_event_id set) before processing — ensuring they only act on events
that have been durably committed to the governance record.

---

## 5. Engine Deployment Model

### Inferential Engine

**Characteristics:** Stateless per-request. CPU-bound for NLP classification.
Vector similarity computation for matching.

**Deployment:** Horizontally scalable. Multiple instances behind an internal
load balancer. NLP model loaded once per instance at startup (model weights
shared via read-only volume).

```
inferential-engine (N instances)
  — language: Python (NLP ecosystem: spaCy / sentence-transformers)
  — model storage: read-only shared volume (model weights)
  — DB connection: inferential_ro role
  — Bus connection: inferential.consumer group
  — Internal RPC: HTTP on isolated internal network
  — No public network access
```

**Scaling trigger:** pending queue depth on `inferential.consumer` group.
Auto-scale to drain queue. Governance events are bursty (many events in a
short period when a large Cell is active), not continuous.

---

### Insight Engine

**Characteristics:** Stateless for scheduling and notification. LLM-dependent
for summarisation and drafting. The LLM calls are the computational bottleneck.

**Deployment:** Two sub-components with different scaling profiles.

```
insight-engine-scheduler (N instances, lightweight)
  — handles: scheduling, notifications, fact-checking (rule-based)
  — language: Go or Node.js
  — DB connection: insight_ro role
  — Bus connection: insight.consumer group
  — Internal RPC: HTTP on isolated internal network
  — No LLM dependency

insight-engine-llm (M instances, GPU or API-backed)
  — handles: draft proposal generation, motion drafting, rolling minutes
  — language: Python
  — LLM backend: configurable (see §6 — LLM options)
  — Only called on-demand (sponsor click, crystallise trigger)
  — Not a bus consumer — invoked by insight-engine-scheduler or API server
  — No DB access (receives content payload in request, returns structured output)
```

The LLM sub-component has no database access and no bus access. It receives
text, returns structured text. This makes it easy to swap providers and limits
the blast radius if the LLM backend has issues — governance state is unaffected.

---

### Integrity Engine

**Characteristics:** Stateful (must maintain hash chain state). Single-writer
per org. High trust, maximum isolation.

**Deployment:** One active instance per org shard. Standby replica for failover.
Not horizontally scalable for writes — by design.

```
integrity-engine (1 active + 1 standby per org shard)
  — language: Go (performance, low-level control, strong typing)
  — DB connection: integrity_rw role (exclusive write grants)
  — Bus connection: integrity.consumer group (ALL events)
  — Internal RPC: restricted to API server (enact-resolution endpoint only)
  — No public network access
  — Runs in isolated network segment
  — Failover: standby takes over within 30s on active failure
              hash chain state loaded from last committed ledger event
```

**Why Go for the Integrity Engine:** the hash chain computation and atomic
transaction logic benefit from explicit concurrency control and strong typing.
The engine must never corrupt the ledger — a GC pause or async surprise is
an unacceptable risk here.

**Org sharding:** at scale, orgs are distributed across Integrity Engine
shards. One shard handles multiple orgs; one org is handled by exactly one
active Integrity Engine instance. Shard assignment is static and only changes
on deliberate rebalancing (maintenance operation, not automatic).

---

## 6. Ledger Backend Options

The ledger is designed with a pluggable storage backend. The hash chain
and data model are consistent regardless of backend.

### Option A — PostgreSQL (default, v1.0)

**Recommended for:** most orgs, all sizes.

```
+ Familiar operational model
+ Full SQL query capability for audit
+ ACID transactions
+ Row-level security and append-only triggers already designed
+ Chain verification possible via SQL window functions
- Immutability is enforced by application + triggers, not natively
- External auditors must trust the operator's DB integrity
```

For v1.0, PostgreSQL with the append-only trigger model and cryptographic
hash chain is the default. The hash chain means that even if an operator
wanted to tamper with a ledger row, the tampering would be detectable by
any party with read access — they can recompute the chain and find the
first broken link.

---

### Option B — Append-Only Event Store (EventStoreDB)

**Recommended for:** orgs that want native append-only guarantees at the
storage layer, not just the application layer.

```
+ Natively append-only — no triggers needed
+ Built-in event sourcing primitives
+ Stream-per-subject maps well to our model
+ Chain integrity enforced at storage level
- Less familiar operationally than PostgreSQL
- SQL query capability reduced (projections are the query model)
- Adds operational complexity for joins/reporting
```

EventStoreDB's persistent subscriptions can replace the NATS bus for event
delivery, simplifying the topology at the cost of flexibility.

---

### Option C — Blockchain Ledger (audit-critical orgs)

**Recommended for:** public-facing governance bodies, DAOs, orgs requiring
external, trustless verification of governance records.

```
+ Maximum immutability — no single operator can tamper
+ External auditability without trusting the operator
+ Aligns with PAAS source doc recommendation for max auditability
- Significant operational complexity
- Write latency (block confirmation time)
- Cost per write (gas fees on public chains, node costs on private)
- Governance events are low-frequency, so cost is manageable
```

For blockchain integration, the governance events are written as transactions
to the chain. The `ledger_event_id` in the data model maps to the transaction
hash. The application database (PostgreSQL) is still the primary query store —
the chain is the verification layer, not the operational store.

Suitable chains for v1.1+ consideration:
- Private/permissioned: Hyperledger Fabric, Quorum
- Public with low fees: Polygon, Arbitrum
- Maximum decentralisation: Ethereum mainnet (high cost, for highest-stakes orgs)

---

### Comparison

| Criterion | PostgreSQL | EventStoreDB | Blockchain |
|---|---|---|---|
| Immutability | Enforced (triggers + chain) | Native | Cryptographic |
| External auditability | Operator-trusted | Operator-trusted | Trustless |
| Query capability | Full SQL | Projections | External indexer needed |
| Operational complexity | Low | Medium | High |
| Write latency | <5ms | <10ms | Seconds (chain-dependent) |
| v1.0 recommendation | ✓ Default | ✓ Alternative | v1.1+ |

---

## 7. Multi-Org Tenancy Model

### Logical Tenancy (all tiers)

Every table carries `org_id`. All queries at the application layer are
scoped by `org_id` — enforced in the ORM/query layer, not just convention.

Row-Level Security policies enforce this at the database layer as well:

```sql
-- Applied to all tables with org_id
CREATE POLICY org_isolation ON <table>
  FOR ALL
  USING (org_id = current_setting('app.current_org_id')::uuid);
```

The `app.current_org_id` session variable is set by the connection pool
manager when a connection is checked out for a request. An API server
handling org A's requests cannot accidentally query org B's data.

---

### Physical Tenancy Options

**Tier 1 — Shared database, schema per org**

```
PostgreSQL cluster
  └── schema: org_<slug>
        └── all tables (prefixed by schema)

Connection: app_rw connects to schema org_<slug> only

Pros: strong isolation, independent schema evolution per org,
      no cross-org query possible at the SQL level
Cons: schema management at scale (100s of orgs = 100s of schemas),
      migrations require per-schema execution
```

Recommended for: up to ~200 orgs on a shared deployment.

**Tier 2 — Database per org (high isolation)**

```
PostgreSQL cluster per org (or small group of orgs)
  — each org has its own database instance
  — Integrity Engine shard maps 1:N to orgs

Pros: maximum data isolation, independent scaling, independent backup/restore
Cons: higher infrastructure cost, more complex operational overhead
```

Recommended for: enterprise orgs, high-sensitivity governance bodies,
orgs that require contractual data isolation guarantees.

**Tier 3 — Self-hosted**

An org can run the entire Orb Sys stack on their own infrastructure.
The architecture is designed to support this:
- All services are containerised (Docker)
- The event bus, database, and engines are all self-contained
- No external dependencies except the LLM backend (configurable)
- Ledger can be PostgreSQL, EventStoreDB, or blockchain (operator's choice)

Self-hosted orgs carry their own operational responsibility. The cryptographic
hash chain still provides tamper-evidence even in self-hosted deployments —
any member with read access to the ledger can verify chain integrity
independently of the operator.

---

### Engine Tenancy

```
Inferential Engine — shared across orgs
  NLP models are org-agnostic. Request context carries org_id.
  No cross-org data leakage risk (stateless, no persistent org data).

Insight Engine — shared across orgs
  LLM calls are stateless. Rolling minutes stored per-org in app DB.
  No cross-org data leakage risk.

Integrity Engine — per-org shard
  Owns the hash chain state. Must be per-org to maintain chain integrity.
  Org A's Integrity Engine instance has no access to org B's database
  schema or connection credentials.
```

---

## 8. Infrastructure Topology

### v1.0 Reference Deployment

```
┌─────────────────────────────────────────────────────────────┐
│                      CLOUD PROVIDER                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   PUBLIC ZONE                         │   │
│  │                                                      │   │
│  │   Load Balancer (TLS termination)                    │   │
│  │   API Gateway (rate limiting, token routing)         │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                       │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │                 APPLICATION ZONE                      │   │
│  │                                                      │   │
│  │   API Server (N pods, stateless, horizontal scale)   │   │
│  │   Blind Review API (M pods, isolated network)        │   │
│  │   Notification Service (push/email/webhook)          │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │ internal only                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │                  ENGINE ZONE                          │   │
│  │   (no public ingress — internal RPC only)            │   │
│  │                                                      │   │
│  │   Inferential Engine (K pods)                        │   │
│  │   Insight Engine — Scheduler (L pods)                │   │
│  │   Insight Engine — LLM (P pods, GPU if self-hosted)  │   │
│  │   Integrity Engine (1 active + 1 standby per shard)  │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │ internal only                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │                   DATA ZONE                           │   │
│  │   (no ingress except from Engine Zone)               │   │
│  │                                                      │   │
│  │   PostgreSQL cluster (primary + read replicas)       │   │
│  │   NATS JetStream cluster (3 nodes, quorum writes)    │   │
│  │   Object Store (S3-compatible, for file attachments, │   │
│  │     commons snapshots, STF report PDFs)              │   │
│  │   LLM Backend (self-hosted) OR                       │   │
│  │     External API proxy (no raw content egress)       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Network Segmentation Rules

```
Public Zone → Application Zone:     HTTPS 443 only
Application Zone → Engine Zone:     internal RPC (gRPC or HTTP/2), no internet
Engine Zone → Data Zone:            DB ports, NATS ports only, no internet
Data Zone → Engine Zone:            NATS subscription callbacks only
Integrity Engine → Application:     blocked (Integrity Engine never calls the API)
Blind Review API → App DB:          blind_review_rw role, isolated connection pool
LLM Backend → internet:             blocked if self-hosted
External LLM proxy:                 HTTPS egress only, content stripped of org_id
```

The LLM backend deserves specific attention: if using an external LLM API
(e.g. a hosted model), the content sent for summarisation or drafting should
be stripped of identifying information (member handles, org name) before
egress. The Insight Engine handles this stripping in the request preparation
layer. The returned text is re-attributed by the Insight Engine before
returning to the application layer.

---

## 9. Deployment Tiers

Three configurations depending on org size and requirements:

### Tier 1 — Starter (small orgs, ≤ 100 members)

```
Single cloud host (or VPS)
  — PostgreSQL (shared instance, schema per org)
  — NATS JetStream (single node — acceptable for low traffic)
  — All three engines on the same host (separate processes)
  — LLM backend: external API (low volume, low cost)
  — No HA — single point of failure acceptable at this scale
  — Backup: daily snapshot, restore within 4h

Monthly infrastructure cost estimate: $50–150 USD
```

---

### Tier 2 — Standard (medium orgs, 100–2000 members)

```
Multi-host, single availability zone
  — PostgreSQL primary + 1 read replica
  — NATS JetStream 3-node cluster (quorum writes)
  — Inferential Engine: 2–3 pods
  — Insight Engine Scheduler: 2 pods
  — Insight Engine LLM: 1–2 pods (GPU or external API)
  — Integrity Engine: 1 active + 1 standby
  — HA for all stateful components
  — Backup: continuous WAL archiving, restore within 30m

Monthly infrastructure cost estimate: $300–800 USD
```

---

### Tier 3 — Enterprise / Self-Hosted (large orgs, 2000+ members, or full control)

```
Multi-zone, multi-region optional
  — PostgreSQL: database per org, or schema-per-org on dedicated cluster
  — NATS JetStream: 5-node cluster across availability zones
  — Inferential Engine: auto-scaling pod group
  — Insight Engine: separate scheduler and LLM deployments, GPU nodes
  — Integrity Engine: per-org shard, active/standby per shard
  — Ledger: PostgreSQL default, EventStoreDB or blockchain available
  — Full self-hosted option: Kubernetes manifests provided
  — SLA-grade backup + restore

Monthly infrastructure cost estimate: $1,500–5,000+ USD (highly variable)
```

---

## 10. Failure Modes & Recovery

### Integrity Engine Failure

The most sensitive failure mode. If the active Integrity Engine instance
fails mid-write:

```
Scenario: Integrity Engine fails after writing 3 of 5 parameters
          in a sys-bound Resolution atomic transaction.

Prevention: the atomic transaction (see API v1 §5e) wraps all parameter
            writes in a single PostgreSQL transaction. If the process dies
            mid-transaction, the transaction is rolled back automatically.
            Partial writes are not possible.

Recovery:   Standby takes over within 30s.
            On startup, reads last committed event from ledger.
            Re-processes any events that were in-flight (NATS provides
            at-least-once delivery — Integrity Engine is idempotent on
            event IDs it has already processed).
            Hash chain resumes from last valid event_hash.
```

### Event Bus Failure

```
Scenario: NATS cluster loses quorum (2 of 3 nodes down).

Behaviour: API server continues to accept requests. Governance state
           writes to the DB succeed. Events queue locally on the API
           server (in-memory buffer with configurable overflow to disk).

Recovery:  NATS quorum restored. Queued events are delivered.
           Engines process in order. Ledger eventually consistent.
           No governance state is lost — it was in the DB already.

Limit:     Extended NATS outage (> hours) may exhaust local buffer.
           Alert threshold: 15 minutes queue backlog.
```

### LLM Backend Failure

```
Scenario: LLM backend (Insight Engine) is unavailable.

Behaviour: On-demand draft proposal returns 503 with message:
           "Proposal drafting is temporarily unavailable.
            You may sponsor the thread with a manually written
            founding mandate."
           The sponsor flow continues — manual founding mandate
           accepted. The engine is assistive, not required.

           Motion drafting returns same 503. Member can write
           the motion specification manually. Engine is assistive.

           Rolling minutes stop updating. Raw Cell record
           remains fully accessible and complete.

Recovery:  No governance state affected. Drafts and minutes
           resume when LLM backend recovers. No replay needed.
```

### Database Failure (primary down)

```
Scenario: PostgreSQL primary fails.

Behaviour: Read replica promoted to primary (automatic with managed
           PostgreSQL services, or manual with self-hosted).
           Promotion time: 30–60s typical.

During promotion: API server returns 503 on write endpoints.
                  Read endpoints continue serving from replica.
                  Event bus buffers new events.

Recovery:  New primary comes online. Buffered events processed.
           Ledger resumes from last committed event.
```

### Ledger Chain Break (tampering detection)

```
Scenario: A ledger row is modified directly in the database
          (bypassing application layer — e.g. a compromised DB admin).

Detection: Any member can run GET /ledger/verify, which recomputes
           the hash chain. The first event where
           event_hash != SHA-256(id + payload + prev_hash) is flagged.

Response:  The break is logged as a governance integrity event.
           All events after the break point are marked 'unverified'
           pending investigation.
           This is a jSTF-level event — Judicial Circle is notified.
           The tampered event and all subsequent events require
           human review before governance state derived from them
           is considered authoritative.
```

---

*Deployment Architecture v1.0 — compiled alongside OrbSys_api_v1.md.*
*Next: onboarding & bootstrapping flow — how an org comes into existence,
founding Circle ratification, initial parameter set, pilot phase structure.*
