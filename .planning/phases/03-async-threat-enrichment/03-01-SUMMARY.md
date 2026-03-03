---
phase: 03-async-threat-enrichment
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, enrichment, queue, retry]
requires:
  - phase: 02-canonical-prisoner-data
    provides: Canonical prisoner schema and deterministic migration test harness.
provides:
  - Pending-first enrichment persistence fields on prisoners.
  - Durable enrichment_jobs queue table with FIFO claim indexes.
  - Migration regression tests validating schema shape and defaults.
affects: [ingest, prisoner-query, async-enrichment-worker]
tech-stack:
  added: []
  patterns: [pending-first enrichment status, db-backed FIFO queue, migration regression testing]
key-files:
  created:
    - backend/app/models/enrichment_job.py
    - backend/alembic/versions/20260303_05_async_enrichment_foundation.py
  modified:
    - backend/app/core/config.py
    - backend/app/models/prisoner.py
    - backend/app/models/__init__.py
    - backend/tests/enrichment/test_enrichment_schema_migration.py
key-decisions:
  - "Persist enrichment reason metadata as JSON on both prisoners and queue rows to preserve explicit null-intel explanations."
  - "Use status+available_at+created_at+id as the FIFO claim index contract for future worker claiming."
patterns-established:
  - "Prisoner enrichment state is explicit (`pending` default) and never inferred from missing fields."
  - "Async queue durability is modeled in SQL first, then consumed by worker logic in later plans."
requirements-completed: [INTL-02, INTL-03, INTL-04]
duration: 5 min
completed: 2026-03-03
---

# Phase 3 Plan 01: Async Enrichment Foundation Summary

**Async enrichment persistence now ships with pending-by-default prisoner status fields and a durable FIFO queue schema for deferred threat-intel processing.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T14:05:57Z
- **Completed:** 2026-03-03T14:11:02Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added enrichment lifecycle and intel/provenance fields to canonical prisoner persistence with explicit nullable intel values.
- Introduced durable `enrichment_jobs` ORM model and migration table for queued/in-progress/failed/completed workflow storage.
- Added migration regression tests proving pending defaults, queue schema linkage, and deterministic repeat upgrades.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define enrichment status/intel contracts on prisoners and durable queue model** - `2f2a09c`, `9744d33` (test, feat)
2. **Task 2: Create migration and schema regression coverage for enrichment foundation** - `4f5a763`, `42c00f8` (test, feat)

**Plan metadata:** pending final docs commit

_Note: TDD tasks produced RED and GREEN commits per task._

## Files Created/Modified
- `backend/app/core/config.py` - Added typed enrichment timeout/retry/backoff settings and removed duplicated rate-limit declarations.
- `backend/app/models/prisoner.py` - Added enrichment status/intel/provenance columns and queue relationship.
- `backend/app/models/enrichment_job.py` - Added durable queue ORM model with FIFO claim indexes and retry metadata.
- `backend/app/models/__init__.py` - Exported `EnrichmentJob` so metadata loading includes queue schema.
- `backend/alembic/versions/20260303_05_async_enrichment_foundation.py` - Added migration for prisoner enrichment fields and queue table/indexes.
- `backend/tests/enrichment/test_enrichment_schema_migration.py` - Added ORM and migration regression tests for enrichment schema contracts.

## Decisions Made
- Used explicit JSON metadata containers for enrichment reasons so null intel values always keep a machine-readable explanation.
- Added server defaults (`pending`, `queued`, retry counters, metadata defaults) in migration to keep existing rows and future inserts deterministic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed duplicate config declarations while adding enrichment settings**
- **Found during:** Task 1 (Define enrichment status/intel contracts on prisoners and durable queue model)
- **Issue:** `config.py` had duplicate rate-limit fields and validators that risked drift when extending settings.
- **Fix:** Consolidated declarations and validators while adding enrichment timeout/retry/backoff configuration.
- **Files modified:** `backend/app/core/config.py`
- **Verification:** `cd backend && .venv/bin/pytest tests/enrichment/test_enrichment_schema_migration.py::test_enrichment_model_defaults_pending_and_null_intel_fields -q`
- **Committed in:** `9744d33`

**2. [Rule 3 - Blocking] pytest binary missing from PATH in execution shell**
- **Found during:** Task 1 RED verification
- **Issue:** Plan command `pytest ...` failed with `command not found`.
- **Fix:** Switched verification commands to `backend/.venv/bin/pytest` for deterministic execution in project environment.
- **Files modified:** None (execution environment only)
- **Verification:** All task and plan verification commands passed via `.venv/bin/pytest`.
- **Committed in:** N/A (no code change)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were execution-critical and kept scope aligned to enrichment persistence contracts.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Prisoners now persist explicit async-enrichment lifecycle and nullable intel metadata needed by worker/runtime plans.
- Durable queue schema and migration guards are in place for implementing claiming/retry processing in subsequent plans.

## Self-Check: PASSED
- Verified required files exist on disk.
- Verified all task commit hashes are present in git history.

---
*Phase: 03-async-threat-enrichment*
*Completed: 2026-03-03*
