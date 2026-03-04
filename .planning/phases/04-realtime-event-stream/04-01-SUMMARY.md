---
phase: 04-realtime-event-stream
plan: 01
subsystem: api
tags: [realtime, websocket, pydantic, fanout]
requires:
  - phase: 03-async-threat-enrichment
    provides: Canonical prisoner summary and enrichment state fields consumed by realtime payload contracts.
provides:
  - Strict, schema-locked realtime envelope and payload contracts for all Phase 4 event types.
  - In-process subscribe/publish fanout bus with centralized event metadata generation.
  - Realtime tests proving unknown event rejection and deterministic publish-order fanout.
affects: [phase-04, websocket-delivery, mutation-publishers]
tech-stack:
  added: []
  patterns: [strict-pydantic-contracts, typed-fanout-bus, tdd-red-green]
key-files:
  created:
    - backend/app/schemas/realtime.py
    - backend/app/realtime/event_bus.py
    - backend/tests/realtime/test_event_schemas.py
    - backend/tests/realtime/test_event_bus.py
  modified:
    - backend/app/core/config.py
    - backend/app/realtime/__init__.py
key-decisions:
  - "Realtime envelopes map each event literal to one payload model so malformed event/payload pairings fail validation immediately."
  - "The event bus injects ordering metadata and envelope timestamps centrally, so publishers do not hand-roll sequence/timing fields."
patterns-established:
  - "Pattern: Realtime payloads always carry ordering metadata (`publish_sequence`, `source_updated_at`) for newest-wins reducers."
  - "Pattern: Read-side services publish via an in-process typed bus contract, decoupled from websocket transport internals."
requirements-completed: [RT-01, RT-02, RT-03, SEC-04]
duration: 6min
completed: 2026-03-04
---

# Phase 4 Plan 1: Realtime Contract and Fanout Foundation Summary

**Typed realtime event envelopes and a deterministic in-process fanout bus now provide the shared publish contract for websocket sync, prisoner updates, and stats cadence events.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-04T00:40:07Z
- **Completed:** 2026-03-04T00:45:20Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added strict Pydantic v2 realtime event schemas with explicit event-name allowlist and `extra="forbid"` payload contracts.
- Added typed payload models for welcome/sync lifecycle, snapshot chunks, prisoner summaries with stale-detail hints, and stats updates.
- Implemented a reusable async event bus with subscribe/unsubscribe/publish fanout and centralized metadata generation for IDs, timestamps, and ordering.
- Verified behavior with dedicated realtime schema and fanout tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create strict realtime event envelope and payload schemas**
   - `83120c7` (`test`): failing schema tests (RED)
   - `c5d129a` (`feat`): realtime schema + settings implementation (GREEN)
2. **Task 2: Implement in-process realtime event bus contract for typed fanout**
   - `903c12a` (`test`): failing event-bus tests (RED)
   - `9ebfce7` (`feat`): event bus implementation + exports (GREEN)

**Plan metadata:** pending final docs commit

## Files Created/Modified
- `backend/app/core/config.py` - Added typed realtime protocol/cadence settings.
- `backend/app/schemas/realtime.py` - Added strict event envelope and payload schema contracts.
- `backend/app/realtime/event_bus.py` - Added typed subscribe/unsubscribe/publish fanout contract.
- `backend/app/realtime/__init__.py` - Exported realtime bus contract.
- `backend/tests/realtime/test_event_schemas.py` - Added schema validation and UTC normalization coverage.
- `backend/tests/realtime/test_event_bus.py` - Added deterministic fanout ordering/unsubscribe coverage.

## Decisions Made
- Bound each event literal to a dedicated payload model and validated pairings in the envelope model validator.
- Generated ordering metadata in bus publish flow to avoid duplicate ad-hoc timestamp/sequence logic in future publishers.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Python 3.9 typing compatibility for realtime schemas**
- **Found during:** Task 1 implementation verification
- **Issue:** Pydantic on Python 3.9 rejected `str | None` syntax when importing realtime schema models.
- **Fix:** Replaced `str | None` with `Optional[str]` in realtime payload model typing.
- **Files modified:** `backend/app/schemas/realtime.py`
- **Verification:** `cd backend && .venv/bin/pytest tests/realtime/test_event_schemas.py -q`
- **Commit:** `c5d129a`

**2. [Rule 1 - Bug] Event bus injected welcome-only fields into stats payload**
- **Found during:** Task 2 implementation verification
- **Issue:** Bus added `server_time` to all events, violating strict stats payload schema (`extra="forbid"`).
- **Fix:** Scoped `server_time` auto-injection to `welcome` events only.
- **Files modified:** `backend/app/realtime/event_bus.py`
- **Verification:** `cd backend && .venv/bin/pytest tests/realtime/test_event_bus.py::test_event_bus_fanout_preserves_publish_order -q`
- **Commit:** `9ebfce7`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Auto-fixes were required for environment compatibility and strict schema correctness; no scope creep introduced.

## Issues Encountered
- `state advance-plan`, `state update-progress`, and `state record-session` could not parse legacy `STATE.md` position/session blocks.
- Applied manual fallback by updating `Current Position`, progress text, and session continuity fields directly in `STATE.md` after recording metrics/decisions via supported commands.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Realtime schemas and fanout contract are in place for websocket transport wiring and mutation publisher integration.
- No blockers identified for subsequent Phase 4 plans.

---
*Phase: 04-realtime-event-stream*
*Completed: 2026-03-04*

## Self-Check: PASSED
- Verified summary file exists on disk.
- Verified task commits exist in git history: `83120c7`, `c5d129a`, `903c12a`, `9ebfce7`.
