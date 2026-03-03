---
phase: 02-canonical-prisoner-data
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, ingest, idempotency, canonical-data]
requires:
  - phase: 02-canonical-prisoner-data
    provides: Canonical source_ip prisoner schema and protocol/history tables from 02-01.
provides:
  - Canonical ingest mutation keyed by source_ip with replay-safe delivery gating.
  - Persisted credential, command, and download histories with deterministic cap pruning.
  - Regression coverage for protocol aggregation, duplicate safety, and history retention semantics.
affects: [data-query-api, retention-lifecycle, dashboard-prisoner-detail]
tech-stack:
  added: []
  patterns: [insert-first idempotency, canonical source_ip mutation, append-then-prune history caps]
key-files:
  created:
    - backend/tests/ingest/test_canonical_ingest.py
  modified:
    - backend/app/services/ingest_service.py
    - backend/app/core/config.py
    - backend/tests/ingest/test_idempotency.py
key-decisions:
  - "Accepted ingest deliveries mutate a single canonical prisoner selected only by source_ip; protocol attempts are tracked in prisoner_protocol_activities."
  - "Credential values are masked before persistence and history pruning keeps newest entries by deleting oldest rows ordered by observed_at then id."
patterns-established:
  - "Canonical ingest mutation path: delivery insert gate -> prisoner/protocol updates -> detail history append -> deterministic cap prune."
  - "History-cap settings are typed runtime config so test and production cap profiles share one validation path."
requirements-completed: [DATA-01, DATA-02]
duration: 5 min
completed: 2026-03-03
---

# Phase 2 Plan 2: Canonical Ingest Mutation Summary

**Canonical source-IP ingest mutation now persists masked, capped credential/command/download histories while preserving duplicate-safe replay semantics.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T12:41:18Z
- **Completed:** 2026-03-03T12:46:57Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Reworked ingest mutation to resolve prisoners by `source_ip`, increment `attempt_count` once per accepted delivery, and preserve per-protocol attempt activity.
- Added persisted detail history writes for credentials, commands, and downloads using append-only rows with protocol/timestamp context.
- Implemented deterministic oldest-first cap pruning and credential masking semantics, plus focused ingest regression tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Canonicalize ingest mutation path by source_ip with protocol activity rollups**
2. `cca4dcf` `test(02-02)` RED: failing canonical aggregation + duplicate-attempt guards
3. `aecceea` `feat(02-02)` GREEN: canonical source_ip ingest mutation + protocol attempt updates
4. **Task 2: Persist sectioned credential/command/download history with balanced caps**
5. `76e47cc` `test(02-02)` RED: failing cap-pruning and masking history assertions
6. `dfe194e` `feat(02-02)` GREEN: config caps + append/mask/prune history implementation

## Files Created/Modified

- `backend/app/services/ingest_service.py` - Canonical mutation logic, protocol activity updates, detail history persistence, and deterministic pruning.
- `backend/app/core/config.py` - Typed balanced history cap settings (`200/400/150`) with validation.
- `backend/tests/ingest/test_idempotency.py` - Duplicate replay tests now assert attempt counters remain unchanged on duplicate deliveries.
- `backend/tests/ingest/test_canonical_ingest.py` - Canonical multi-protocol aggregation and history cap/masking regression tests.

## Decisions Made

- Canonical identity lookup in ingest now uses `source_ip` only; protocol-specific counting is delegated to `prisoner_protocol_activities`.
- Credential persistence masks secrets before database write while preserving username context for analyst workflows.
- Pruning strategy is deterministic and oldest-first across each history section using `(observed_at ASC, id ASC)`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pytest command unavailable in shell PATH**
- **Found during:** Task 1 RED verification
- **Issue:** `pytest` command was unavailable, blocking required test execution.
- **Fix:** Used project virtualenv executable `.venv/bin/pytest` for all verification commands.
- **Files modified:** None
- **Verification:** All task and plan verification commands passed with virtualenv pytest.
- **Committed in:** N/A (execution environment adjustment)

**2. [Rule 1 - Bug] Naive vs aware datetime comparison during seen-window updates**
- **Found during:** Task 1 GREEN verification
- **Issue:** SQLite returned naive datetimes, causing `TypeError` when compared with aware ingest timestamps.
- **Fix:** Added UTC coercion before min/max window comparison in ingest service.
- **Files modified:** `backend/app/services/ingest_service.py`
- **Verification:** `tests/ingest/test_idempotency.py` and canonical ingest tests pass.
- **Committed in:** `aecceea`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Fixes were minimal and correctness-oriented; no scope creep.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Canonical ingest now emits persisted detail history needed by prisoner detail query APIs in `02-03`.
- Duplicate replay guarantees remain intact under concurrent submissions.

## Self-Check: PASSED

- Found `.planning/phases/02-canonical-prisoner-data/02-02-SUMMARY.md`.
- Found `backend/tests/ingest/test_canonical_ingest.py`.
- Verified commits: `cca4dcf`, `aecceea`, `76e47cc`, `dfe194e`.

---
*Phase: 02-canonical-prisoner-data*
*Completed: 2026-03-03*
