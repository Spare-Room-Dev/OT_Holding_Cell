---
phase: 04-realtime-event-stream
plan: 04
subsystem: realtime
tags: [websocket, realtime, stats, fastapi, sqlalchemy]
requires:
  - phase: 04-02
    provides: reconnect-safe sync lifecycle and websocket read-only channel
  - phase: 04-03
    provides: prisoner lifecycle mutation publishers
provides:
  - changed-only periodic stats broadcasting
  - canonical realtime stats snapshot service reused by reconnect sync
  - end-to-end reconnect plus live stream verification
  - realtime stream operational verification runbook
affects: [phase-04-realtime-event-stream, phase-05-responsive-analyst-dashboard, operations]
tech-stack:
  added: []
  patterns: [shared realtime event-bus singleton, lifespan-managed background broadcaster]
key-files:
  created:
    - backend/app/services/realtime_stats_service.py
    - backend/app/realtime/stats_broadcaster.py
    - backend/tests/realtime/test_stats_broadcaster.py
    - backend/tests/realtime/test_realtime_stream_e2e.py
    - docs/ops/realtime-stream.md
  modified:
    - backend/app/realtime/snapshot_service.py
    - backend/app/realtime/event_bus.py
    - backend/app/realtime/publishers.py
    - backend/app/realtime/socket_server.py
    - backend/app/main.py
key-decisions:
  - "Use one shared process-local realtime event bus for mutation publishers and websocket fanout delivery."
  - "Manage stats broadcasting via FastAPI lifespan so startup/shutdown is deterministic and leak-free."
  - "Derive reconnect snapshot stats and periodic live stats from one canonical service to keep semantics aligned."
patterns-established:
  - "Realtime stats are emitted only when aggregate snapshots change."
  - "Reconnect snapshots and live updates share canonical aggregation paths."
requirements-completed: [RT-03]
duration: 9 min
completed: 2026-03-04
---

# Phase 4 Plan 4: Realtime Stream Fidelity Summary

**Changed-only `stats_update` broadcasting with canonical snapshot aggregation, lifecycle-managed background cadence, and verified reconnect plus live stream continuity.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-04T01:01:38Z
- **Completed:** 2026-03-04T01:11:08Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Implemented a dedicated realtime stats snapshot service and async cadence broadcaster that emits only when aggregate values change.
- Wired broadcaster startup/shutdown into FastAPI lifespan so background stats emission is consistent and cleanup-safe.
- Added end-to-end websocket test coverage for reconnect snapshot recovery plus continued live prisoner and stats events on one session.
- Added operations runbook instructions to verify lifecycle ordering, changed-only cadence behavior, and reconnect correctness.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement deterministic stats snapshot service and changed-only broadcaster**
   - `fac5766` (test): failing RED tests for stats snapshot + broadcaster cadence
   - `689ad6b` (feat): stats service + broadcaster + snapshot integration
2. **Task 2: Wire lifecycle and validate reconnect/live continuity**
   - `5ee0a8b` (test): failing RED lifecycle + E2E reconnect/live tests
   - `f2225e3` (feat): shared bus fix, lifespan broadcaster wiring, E2E pass, ops runbook

## Files Created/Modified
- `backend/app/services/realtime_stats_service.py` - Canonical current/lifetime aggregate stats computation.
- `backend/app/realtime/stats_broadcaster.py` - Background cadence broadcaster with changed-only emission.
- `backend/app/realtime/snapshot_service.py` - Reuses canonical stats service for reconnect snapshots.
- `backend/app/realtime/event_bus.py` - Shared singleton accessor for process-local realtime bus.
- `backend/app/realtime/publishers.py` - Uses shared bus singleton for mutation publishes.
- `backend/app/realtime/socket_server.py` - Subscribes websocket fanout to shared bus.
- `backend/app/main.py` - Lifespan-managed stats broadcaster startup/shutdown.
- `backend/tests/realtime/test_stats_broadcaster.py` - Stats snapshot and changed-only cadence tests.
- `backend/tests/realtime/test_realtime_stream_e2e.py` - Reconnect + live continuity E2E and lifecycle tests.
- `docs/ops/realtime-stream.md` - Operator verification runbook for stream health and cadence semantics.

## Decisions Made
- Centralized realtime bus ownership in `app.realtime.event_bus.get_realtime_event_bus()` so ingest/enrichment publishers and websocket connections operate on the same fanout channel.
- Kept stats payload schema unchanged while enforcing changed-only emission semantics by comparing canonical snapshots before publish.
- Exposed stats broadcaster on `app.state` to make lifecycle behavior observable and testable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed realtime publisher-to-websocket bus mismatch**
- **Found during:** Task 2 E2E verification
- **Issue:** Ingest/enrichment publishers and websocket fanout used different event bus instances, preventing true live continuity.
- **Fix:** Added shared singleton accessor in `event_bus.py` and switched socket server + publishers to use the same instance.
- **Files modified:** `backend/app/realtime/event_bus.py`, `backend/app/realtime/publishers.py`, `backend/app/realtime/socket_server.py`
- **Verification:** `cd backend && .venv/bin/pytest tests/realtime/test_realtime_stream_e2e.py -q`
- **Committed in:** `f2225e3`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Deviation was required for correctness of live stream behavior and directly enabled RT-03 end-to-end continuity.

## Issues Encountered
- E2E ingest request initially failed with `403` and `422` because test headers/timestamps did not satisfy existing security and freshness rules; test inputs were corrected to use allowlisted forwarded IP and fresh timestamps.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Realtime phase plan set is now complete with verified reconnect and live continuity semantics.
- Dashboard phase can consume stable `stats_update` cadence and websocket lifecycle guarantees.

---
*Phase: 04-realtime-event-stream*
*Completed: 2026-03-04*

## Self-Check: PASSED

- Found summary file: `.planning/phases/04-realtime-event-stream/04-04-SUMMARY.md`
- Verified task commits: `fac5766`, `689ad6b`, `5ee0a8b`, `f2225e3`
