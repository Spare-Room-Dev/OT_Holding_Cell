---
phase: 01-trusted-ingest-boundary
plan: 02
subsystem: api
tags: [fastapi, pydantic, middleware, validation, security]
requires:
  - phase: 01-01
    provides: Shared trusted-forwarder auth and source-IP allowlist dependency.
provides:
  - Strict ingest and heartbeat payload contracts with bounded fields.
  - Early body-size rejection with deterministic 413 response envelope.
  - Sanitized 422 validation responses with internal details logged server-side only.
affects: [01-03-idempotency-flow, ingest-api-contract, heartbeat-api-contract]
tech-stack:
  added: []
  patterns: [two-layer-payload-defense, sanitized-validation-envelope]
key-files:
  created:
    - backend/app/schemas/ingest.py
    - backend/app/schemas/heartbeat.py
    - backend/app/middleware/body_size.py
    - backend/app/middleware/error_handlers.py
    - backend/tests/ingest/test_validation_boundary.py
    - backend/tests/heartbeat/test_validation_boundary.py
  modified:
    - backend/app/api/routes/ingest.py
    - backend/app/api/routes/heartbeat.py
    - backend/app/main.py
key-decisions:
  - "Enforce request-size caps at ASGI middleware level before body parsing."
  - "Return a fixed non-leaky validation envelope for all request-validation failures."
patterns-established:
  - "Bounded schema contracts: strict UUID/literal/timestamp constraints with capped list and string sizes."
  - "Layered rejection model: 413 for oversized payloads before parse, 422 for schema violations after parse."
requirements-completed: [ING-02]
duration: 6 min
completed: 2026-03-03
---

# Phase 01 Plan 02: Trusted Ingest Boundary Summary

**Strict ingest and heartbeat contracts now enforce protocol/UUID/freshness bounds, body-size limits, and sanitized validation error responses.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-03T08:47:30Z
- **Completed:** 2026-03-03T08:53:37Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Added strict Pydantic request models for ingest and heartbeat with hard bounds and freshness checks.
- Added body-size middleware that rejects oversized requests with a deterministic safe `413` envelope.
- Installed global request-validation error handling that returns fixed `422` envelopes without leaking schema internals.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Define strict ingest/heartbeat schema boundaries** - `4159775` (test)
2. **Task 1 GREEN: Implement strict schemas and route model binding** - `aa24683` (feat)
3. **Task 1 Auto-fix: Restore missing heartbeat schema file** - `65a033b` (fix)
4. **Task 2 RED: Add failing body-cap + sanitized error tests** - `1745a1c` (test)
5. **Task 2 GREEN: Implement middleware + sanitized validation handlers** - `aed85ef` (feat)

_Note: TDD tasks produced RED/GREEN commit pairs._

## Files Created/Modified
- `backend/app/schemas/ingest.py` - Strict ingest payload contract with protocol, UUID, freshness, and list-size bounds.
- `backend/app/schemas/heartbeat.py` - Strict heartbeat payload contract with protocol and timestamp freshness validation.
- `backend/app/middleware/body_size.py` - Early request-size gate that returns safe `413` responses.
- `backend/app/middleware/error_handlers.py` - Global sanitized validation handler returning fixed `422` envelope.
- `backend/app/main.py` - Middleware + handler registration before route execution.
- `backend/tests/ingest/test_validation_boundary.py` - Validation boundary matrix, including overflow and oversized-body checks.
- `backend/tests/heartbeat/test_validation_boundary.py` - Heartbeat protocol validation + sanitized error contract checks.

## Decisions Made
- Added a hard `256 KiB` body-size boundary at middleware level to block oversized hostile payloads before parsing.
- Standardized all request validation failures to one safe contract (`validation_error`) while keeping full details only in server logs.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `pytest` command unavailable on PATH**
- **Found during:** Task 1 verification
- **Issue:** Plan verification command failed because `pytest` was not available in shell PATH.
- **Fix:** Switched verification to project-local runner `backend/.venv/bin/pytest`.
- **Files modified:** None
- **Verification:** Task 1 and Task 2 test commands passed using virtualenv pytest.
- **Committed in:** N/A (execution command adjustment only)

**2. [Rule 3 - Blocking] Git index lock race while staging/committing**
- **Found during:** Task 1 implementation commit
- **Issue:** Parallel git operations created transient `.git/index.lock`, interrupting staging flow.
- **Fix:** Re-ran git operations sequentially and validated staged file set before commit.
- **Files modified:** None
- **Verification:** Subsequent commits completed successfully.
- **Committed in:** N/A (workflow adjustment only)

**3. [Rule 1 - Bug] Missing `heartbeat.py` schema file after staging race**
- **Found during:** Task 1 post-commit status check
- **Issue:** Heartbeat schema implementation existed in workspace but was omitted from the previous feature commit.
- **Fix:** Added the missing schema file in an immediate corrective commit.
- **Files modified:** `backend/app/schemas/heartbeat.py`
- **Verification:** Validation boundary suite passed with heartbeat model import and checks active.
- **Committed in:** `65a033b`

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** All deviations were execution correctness fixes; no scope creep and all plan outcomes were delivered.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for `01-03-PLAN.md` (idempotency persistence and replay-safe ingest flow).
- Validation boundary and payload-safety contract are now in place for downstream ingest mutation logic.

## Self-Check: PASSED
- Found summary file: `.planning/phases/01-trusted-ingest-boundary/01-02-SUMMARY.md`
- Verified commits: `4159775`, `aa24683`, `65a033b`, `1745a1c`, `aed85ef`
