---
phase: 02-canonical-prisoner-data
plan: 04
subsystem: database
tags: [sqlalchemy, alembic, retention, cron, data-lifecycle]
requires:
  - phase: 02-canonical-prisoner-data
    provides: Canonical prisoner and ingest delivery persistence from 02-01/02-02.
provides:
  - Daily retention purge service with 30-day prisoner and 7-day delivery cutoffs.
  - Lifetime attempt rollups preserved even after hard-deleting expired prisoner rows.
  - Scheduler-safe retention command and operator runbook for Render cron verification.
affects: [phase-03-enrichment, dashboard-metrics, operations]
tech-stack:
  added: []
  patterns: [transactional retention cycle, rollup upsert-before-delete, cron-json-summary contract]
key-files:
  created:
    - backend/alembic/versions/20260303_04_retention_rollups.py
    - backend/app/models/lifetime_rollup.py
    - backend/app/models/retention_run.py
    - backend/app/services/retention_service.py
    - backend/scripts/run_retention.py
    - docs/ops/retention-cron.md
  modified:
    - backend/app/core/config.py
    - backend/app/models/__init__.py
    - backend/tests/retention/test_retention_job.py
key-decisions:
  - "Retention writes both rollup updates and row purges in one transaction so summary counts always match committed data changes."
  - "The cron entrypoint emits deterministic JSON payloads and non-zero exit status on errors for operator-visible verification."
patterns-established:
  - "Retention flow: compute cutoffs -> aggregate expired attempts into rollups -> purge rows -> persist retention_run metadata."
  - "Operational cron scripts return machine-readable summaries to make scheduler health checks auditable."
requirements-completed: [DATA-03]
duration: 4 min
completed: 2026-03-03
---

# Phase 2 Plan 4: Retention Lifecycle Summary

**Daily retention now purges 30-day prisoners and 7-day deliveries while preserving lifetime breach rollups and exposing scheduler-verifiable run summaries.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T20:58:06+08:00
- **Completed:** 2026-03-03T21:00:14+08:00
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Added retention schema and model coverage for `lifetime_rollups` and `retention_runs`.
- Implemented transactional retention service that preserves aggregate attempt totals before deleting expired rows.
- Added cron-safe execution command and operator documentation for Render daily scheduling and verification.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add retention-rollup schema and transactional purge service**
2. `c34adbb` `feat(02-04)` schema, models, service, and retention verification tests
3. **Task 2: Wire daily retention command entrypoint and operator verification documentation**
4. `fa560d0` `test(02-04)` RED script contract test
5. `e8f5a46` `feat(02-04)` cron entrypoint and ops runbook

## Files Created/Modified

- `backend/alembic/versions/20260303_04_retention_rollups.py` - Migration for retention metadata and rollup tables.
- `backend/app/services/retention_service.py` - Transactional purge + rollup accumulation lifecycle.
- `backend/tests/retention/test_retention_job.py` - Cutoff purge, rerun idempotency, and script contract tests.
- `backend/scripts/run_retention.py` - Scheduler command entrypoint with JSON summary output.
- `docs/ops/retention-cron.md` - Render cron setup and operator verification checklist.

## Decisions Made

- Keep retained headline metrics in dedicated rollup rows keyed by `overall` and `country:*` to avoid double counting across reruns.
- Persist every execution attempt in `retention_runs` so operators can audit success/failure windows independently of scheduler logs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pytest unavailable on PATH during retention verification**
- **Found during:** Task 1 verification
- **Issue:** `pytest` was not available as a shell command, blocking required plan verification.
- **Fix:** Ran tests through project virtualenv executable `backend/.venv/bin/pytest`.
- **Files modified:** None
- **Verification:** Task-level and full retention suite commands both passed.
- **Committed in:** N/A (execution environment adjustment)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** No scope expansion; change was limited to execution command path.

## Issues Encountered

- A transient git index lock appeared while attempting parallel git operations; resolved by re-running commit flow sequentially.

## User Setup Required

External scheduler setup is required in Render:
- Create a daily cron job for `cd /opt/render/project/src/backend && python scripts/run_retention.py`.
- Confirm `DATABASE_URL` exists in backend service env settings.
- Follow verification checklist in `docs/ops/retention-cron.md`.

## Next Phase Readiness

- Retention hygiene and rollup preservation are ready for downstream enrichment and dashboard stats work.
- Remaining phase item is `02-03` query API plan completion.

## Self-Check: PASSED

- Found `.planning/phases/02-canonical-prisoner-data/02-04-SUMMARY.md`.
- Found `backend/scripts/run_retention.py`.
- Verified commits: `c34adbb`, `fa560d0`, `e8f5a46`.

---
*Phase: 02-canonical-prisoner-data*
*Completed: 2026-03-03*
