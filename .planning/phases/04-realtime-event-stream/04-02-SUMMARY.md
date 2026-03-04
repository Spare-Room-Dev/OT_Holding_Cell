---
phase: 04-realtime-event-stream
plan: 02
subsystem: api
tags: [realtime, websocket, snapshot-recovery, security, tdd]
requires:
  - phase: 04-realtime-event-stream
    provides: Typed realtime event envelope and fanout bus from plan 04-01 used by websocket transport.
provides:
  - Reconnect-safe websocket endpoint with deterministic welcome/sync/snapshot/stats/sync_complete lifecycle.
  - Authoritative snapshot builder sourced from canonical prisoner query ordering and persisted lifetime rollups.
  - Read-only inbound websocket handling with origin gating and ignored client message draining.
affects: [phase-04, websocket-delivery, stream-security, dashboard-connection-state]
tech-stack:
  added: []
  patterns: [tdd-red-green, snapshot-then-live-registration, read-only-websocket-channel]
key-files:
  created:
    - backend/app/realtime/connection_manager.py
    - backend/app/realtime/snapshot_service.py
    - backend/tests/realtime/test_socket_stream_api.py
    - backend/tests/security/test_websocket_origin_and_read_only.py
  modified:
    - backend/app/realtime/socket_server.py
    - backend/app/main.py
key-decisions:
  - "Websocket connections only register for live fanout after sync_complete to prevent hydration/live race conditions."
  - "Reconnect stats include current aggregate counts plus persisted lifetime rollup attempts to preserve retention continuity."
patterns-established:
  - "Pattern: Every websocket connect/reconnect follows welcome -> sync_start -> snapshot_chunk -> stats_update -> sync_complete before live fanout."
  - "Pattern: Client-emitted websocket frames are ignored and never dispatched to mutation handlers."
requirements-completed: [RT-03, SEC-04]
duration: 6min
completed: 2026-03-04
---

# Phase 4 Plan 2: Reconnect-Safe Websocket Transport Summary

**Realtime websocket clients now receive deterministic authoritative sync recovery before live stream fanout, with strict origin-gated and read-only inbound channel behavior.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-04T00:52:17Z
- **Completed:** 2026-03-04T01:03:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Implemented `/ws/events` websocket transport with explicit sync lifecycle events and canonical snapshot delivery.
- Added authoritative snapshot/stats assembly using deterministic prisoner ordering from query services and persisted lifetime attempt rollups.
- Added shared realtime connection registry for live envelope fanout and disconnect cleanup.
- Enforced read-only websocket posture: blocked-origin sessions are closed and client frames are drained/ignored while outbound events continue.
- Added focused realtime/security API tests for reconnect lifecycle determinism and read-only security guarantees.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement websocket connect/reconnect sync lifecycle with authoritative snapshot delivery**
   - `c1e1347` (`test`): failing websocket lifecycle API test (RED)
   - `a8e143a` (`feat`): websocket route, snapshot service, connection manager, app wiring (GREEN)
2. **Task 2: Enforce read-only websocket posture and origin security constraints**
   - `3643491` (`test`): failing websocket security tests for blocked origin/read-only behavior (RED)
   - `946fe95` (`feat`): inbound drain hardening and security test pass (GREEN)

**Plan metadata:** pending final docs commit

## Files Created/Modified
- `backend/app/realtime/connection_manager.py` - Added connected-socket registry and typed envelope broadcast cleanup.
- `backend/app/realtime/snapshot_service.py` - Added authoritative reconnect snapshot and stats payload assembly.
- `backend/app/realtime/socket_server.py` - Added websocket endpoint, sync lifecycle emission, origin policy gate, and read-only inbound drain loop.
- `backend/app/main.py` - Mounted websocket router without changing existing REST routers.
- `backend/tests/realtime/test_socket_stream_api.py` - Added deterministic connect/reconnect sync + live handoff API coverage.
- `backend/tests/security/test_websocket_origin_and_read_only.py` - Added blocked-origin and read-only inbound security coverage.

## Decisions Made
- Live fanout registration happens only after `sync_complete` to ensure reconnect hydration is authoritative before streaming deltas.
- Snapshot payload generation reuses canonical prisoner query ordering and enrichment timestamps to keep API and realtime state semantics aligned.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Websocket route used stale import-time DB session factory**
- **Found during:** Task 1 verification
- **Issue:** Tests monkeypatch runtime session factory, but websocket handler bound `SessionFactory` at import time and queried the wrong database.
- **Fix:** Switched websocket snapshot session creation to resolve `SessionFactory` from `app.db.session` at request time.
- **Files modified:** `backend/app/realtime/socket_server.py`
- **Verification:** `cd backend && .venv/bin/pytest tests/realtime/test_socket_stream_api.py::test_websocket_connect_emits_deterministic_sync_lifecycle_before_live_stream -q`
- **Committed in:** `a8e143a`

**2. [Rule 1 - Bug] Snapshot chunk payload omitted nested prisoner ordering metadata**
- **Found during:** Task 1 verification
- **Issue:** `snapshot_chunk` validation failed because each prisoner payload lacked required `ordering` fields.
- **Fix:** Added deterministic per-prisoner ordering metadata during snapshot payload assembly.
- **Files modified:** `backend/app/realtime/snapshot_service.py`
- **Verification:** `cd backend && .venv/bin/pytest tests/realtime/test_socket_stream_api.py::test_websocket_connect_emits_deterministic_sync_lifecycle_before_live_stream -q`
- **Committed in:** `a8e143a`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes were correctness-critical and stayed within planned transport scope.

## Issues Encountered
- None beyond the auto-fixed issues above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Reconnect-safe websocket transport and read-only channel security requirements are now covered by automated tests.
- Phase 4 can proceed with remaining stream behavior work (`04-04`) on top of deterministic sync and lifecycle guarantees.

---
*Phase: 04-realtime-event-stream*
*Completed: 2026-03-04*

## Self-Check: PASSED
- Verified summary file exists: `.planning/phases/04-realtime-event-stream/04-02-SUMMARY.md`
- Verified task commits exist: `c1e1347`, `a8e143a`, `3643491`, `946fe95`
