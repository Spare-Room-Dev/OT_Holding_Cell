---
phase: 04-realtime-event-stream
plan: 03
subsystem: api
tags: [realtime, ingest, enrichment, websocket, event-bus]
requires:
  - phase: 04-realtime-event-stream
    provides: Typed realtime envelope/event bus primitives from plan 04-01 used by mutation publishers.
provides:
  - Canonical prisoner-summary realtime payload publishing helpers with stale-detail hint metadata.
  - Post-commit ingest lifecycle events for new and updated canonical prisoners.
  - Post-persist enrichment completion events with latest merged enrichment fields.
affects: [phase-04, realtime-stream, ingest-mutations, enrichment-worker]
tech-stack:
  added: []
  patterns: [tdd-red-green, commit-then-publish, failure-tolerant-realtime-publish]
key-files:
  created:
    - backend/app/realtime/publishers.py
    - backend/tests/realtime/test_ingest_realtime_events.py
    - backend/tests/realtime/test_enrichment_realtime_events.py
  modified:
    - backend/app/services/prisoner_query_service.py
    - backend/app/services/ingest_service.py
    - backend/app/services/enrichment_queue_service.py
key-decisions:
  - "Mutation publishers resolve payloads from one canonical prisoner summary helper to keep realtime and API list semantics aligned."
  - "Ingest and enrichment continue succeeding when realtime publish fails transiently; failures are logged and not escalated to mutation failures."
patterns-established:
  - "Pattern: Domain services publish realtime lifecycle events only after authoritative persistence commits."
  - "Pattern: Realtime prisoner payloads are full summaries plus stale-detail hint metadata, never partial patches."
requirements-completed: [RT-01, RT-02]
duration: 6min
completed: 2026-03-04
---

# Phase 4 Plan 3: Ingest and Enrichment Realtime Publishers Summary

**Canonical prisoner lifecycle writes now emit `new_prisoner`, `prisoner_updated`, and `prisoner_enriched` realtime events with full summary payloads and stale-detail metadata.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-04T00:49:04Z
- **Completed:** 2026-03-04T00:55:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added reusable realtime publisher helpers that build full prisoner payloads from canonical query contracts.
- Added deterministic single-prisoner summary retrieval for post-mutation publish paths.
- Wired ingest and enrichment services to publish lifecycle events after commit/persist success without breaking mutation success on publish errors.
- Added realtime regression tests for helper payload shape, ingest created/updated selection, duplicate suppression, and enrichment completion emission.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build canonical prisoner realtime publisher helpers from existing summary query contracts**
   - `0fe4943` (`test`): failing helper contract tests (RED)
   - `abb985d` (`feat`): canonical summary helper + realtime publisher utility (GREEN)
2. **Task 2: Publish ingest and enrichment lifecycle realtime events only after persisted state updates**
   - `c659bde` (`test`): failing ingest/enrichment lifecycle emission tests (RED)
   - `f57b873` (`feat`): post-persist lifecycle event publishing integration (GREEN)

**Plan metadata:** pending final docs commit

## Files Created/Modified
- `backend/app/services/prisoner_query_service.py` - Added deterministic `get_prisoner_summary` helper for mutation-driven realtime payload lookups.
- `backend/app/realtime/publishers.py` - Added canonical payload builder, singleton event bus getter, and lifecycle publish wrapper.
- `backend/app/services/ingest_service.py` - Added post-commit `new_prisoner` / `prisoner_updated` publishing with non-blocking failure handling.
- `backend/app/services/enrichment_queue_service.py` - Added post-success `prisoner_enriched` publishing with non-blocking failure handling.
- `backend/tests/realtime/test_ingest_realtime_events.py` - Added helper shape tests and ingest lifecycle emission tests.
- `backend/tests/realtime/test_enrichment_realtime_events.py` - Added enrichment completion emission test.

## Decisions Made
- Realtime payload assembly now always uses the canonical prisoner summary contract rather than mutation-local field assembly.
- Default stale-detail metadata is deterministic (`detail_sync_stale=True`, `detail_last_changed_at` from latest summary/enrichment timestamp).
- Publish failures are treated as transient downstream concerns and logged, preserving ingest/enrichment durability semantics.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ingest realtime tests used stale timestamps outside schema freshness window**
- **Found during:** Task 2 verification
- **Issue:** New ingest realtime tests used fixed historical timestamps rejected by `IngestPayload` freshness validation.
- **Fix:** Switched test payload timestamps to `datetime.now(timezone.utc)` while preserving lifecycle assertions.
- **Files modified:** `backend/tests/realtime/test_ingest_realtime_events.py`
- **Verification:** `cd backend && .venv/bin/pytest tests/realtime/test_ingest_realtime_events.py tests/realtime/test_enrichment_realtime_events.py -q`
- **Committed in:** `f57b873`

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Auto-fix was test-only and required for compatibility with existing ingest boundary validation; no scope creep.

## Issues Encountered
- None beyond the auto-fixed ingest test timestamp freshness mismatch.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Realtime lifecycle events are now emitted from authoritative mutation paths and can be consumed by websocket delivery flow.
- Ready for downstream stats cadence and client consumption work in remaining Phase 4 plans.

---
*Phase: 04-realtime-event-stream*
*Completed: 2026-03-04*

## Self-Check: PASSED
- Verified summary file exists: `.planning/phases/04-realtime-event-stream/04-03-SUMMARY.md`
- Verified task commits exist: `0fe4943`, `abb985d`, `c659bde`, `f57b873`
