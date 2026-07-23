# Changelog

All notable changes to Orbsys will be documented in this file.

## [0.1.0] — 2026-07-23

### Fixed
- **Privacy leak**: `stf.py` no longer returns `subject_member_id` for blind STF types (jSTF, meta-aSTF)
- **Crash bug**: `circles.py` missing import of `get_event_bus`, `GovernanceEvent`, `EventType`
- **Auth bypass**: internal event endpoint returns 503 when `INTERNAL_TOKEN` not configured
- **Motion lifecycle**: `_maybe_close_vote` was never called after `cast_vote` — motions stuck in VOTED state
- **STF enforcement**: `enact_resolution` now requires STF state=COMPLETED and resolution linked to STF
- **Cell access**: closed cells now properly restrict access via `cell.access` field check
- **Pagination**: `dormain_leaderboard` total count now filtered by `org_id`
- **Scoring**: jSTF W_h minimum enforced; `curiosity_fit` default `0.0` → `0.5`; independence exclusion extended
- **Blind service**: env var `DATABASE_URL` → `BLIND_DATABASE_URL`; verdict race condition fixed with `SELECT FOR UPDATE`
- **N+1 query**: `list_cells` batch-loads members instead of per-cell query
- **AttributeError**: `cell.dissolved_at` reference removed (field doesn't exist)
- **Schema nullable**: `CommonsThreadResponse.author`, `CommonsPostResponse.author`, `ContributionResponse.author` now nullable for deleted accounts
- **Double-wrapping**: `new_value` in `file_motion` no longer wrapped in `{"value": ...}`
- **Error leak**: `enact_resolution` error message sanitized — full exception logged server-side only
- **Sponsorship check**: `sponsor_draft` and `confirm_sponsorship` now accept both `"open"` and `"sponsored"` states
- **Auth guard**: Next.js middleware now checks `orbsys_session` cookie, redirects unauthenticated users
- **Refresh race**: refresh mutex prevents concurrent 401 → refresh token races
- **Session restore**: `clearOrgSession` restores platform token; `logout` removes stale keys
- **Handle validation**: `apply_to_join` enforces `^[a-z0-9_-]+$` pattern (2-100 chars)

### Added
- **FK constraints**: `cells.stf_instance_id → stf_instances.id`, `commons_threads.sponsoring_cell_id → cells.id`
- **Alembic migration**: `0007_fk_constraints.py`
- **Enums**: `CellVoteChoice` (yea/nay/abstain), `CommonsThreadState` (open/sponsored/closed/archived)
- **Members list**: `GET /members` endpoint with pagination
- **Frontend members page**: now calls `membersApi.list()` instead of broken `membersApi.feed()`
- **CI pipeline**: GitHub Actions for pytest + ruff lint on push/PR
- **Test suite**: 17 unit tests covering auth, members schemas, pagination, enums, event types
- **Ruff lint**: codebase passes ruff check with E, F, I, UP rules

### Changed
- Internal event endpoint now returns 503 when `INTERNAL_TOKEN` not configured (was bypassing auth)
- Health endpoint returns 503 on DB failure instead of masking errors
- Deadline monitor deduplicates via `NOT EXISTS` guard
