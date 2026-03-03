---
phase: 01-trusted-ingest-boundary
plan: 03
subsystem: database
tags: [fastapi, sqlalchemy, alembic, idempotency, ingest]
requires:
  - phase: 01-01
    provides: Shared trusted-forwarder authentication and allowlist source-IP controls.
  - phase: 01-02
    provides: Strict validated ingest payload schema and safe request envelopes.
provides:
  - Persistent delivery-id uniqueness for replay protection.
  - Transactional insert-first ingest flow that no-ops duplicate submissions.
  - Deterministic duplicate replay response contract with concurrency test coverage.
affects: [phase-02-canonical-prisoner-data, ingest-api-contract, replay-reliability]
tech-stack:
  added: [alembic, sqlalchemy]
  patterns: [insert-first-idempotency-gate, transactional-replay-short-circuit]
key-files:
  created:
    - backend/alembic/env.py
    - backend/alembic/script.py.mako
    - backend/alembic/versions/20260303_01_ingest_deliveries.py
    - backend/app/services/ingest_service.py
    - backend/app/services/__init__.py
  modified:
    - backend/app/models/ingest_delivery.py
    - backend/app/api/routes/ingest.py
    - backend/app/security/forwarder_auth.py
    - backend/tests/ingest/test_idempotency.py
key-decisions:
  - "Gate all ingest mutations behind a first-write delivery insert to guarantee replay safety."
  - "Return HTTP 200 with status duplicate_ignored for duplicate delivery_id submissions."
  - "Bootstrap replay tests from Alembic migrations so schema constraints are verified at the storage layer."
patterns-established:
  - "Idempotency contract: unique delivery_id insert attempts happen before any prisoner mutation."
  - "Duplicate handling contract: duplicate submissions are treated as successful no-op outcomes."
requirements-completed: [ING-03]
duration: 4 min
completed: 2026-03-03
---

# Phase 01 Plan 03: Trusted Ingest Boundary Summary

**Replay-safe ingest now persists unique delivery IDs and guarantees duplicate submissions become deterministic no-op responses without duplicate prisoner mutations.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T09:07:00Z
- **Completed:** 2026-03-03T09:11:05Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Added Alembic migration scaffolding and schema creation for `prisoners` + `ingest_deliveries` with a unique `delivery_id` constraint.
- Implemented transactional insert-first ingest processing that short-circuits duplicates and only mutates prisoner state on first-write deliveries.
- Added API and concurrency tests proving duplicate replay returns `duplicate_ignored` and total prisoner/delivery records remain single-write under parallel duplicate submissions.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing migration coverage** - `1c335cb` (test)
2. **Task 1 GREEN: Implement migration/model support** - `60a6013` (feat)
3. **Task 2 RED: Add failing replay + concurrency tests** - `b07c171` (test)
4. **Task 2 GREEN: Implement replay-safe transactional ingest flow** - `713dede` (feat)

## Files Created/Modified
- `backend/alembic/env.py` - Alembic runtime environment bound to project metadata.
- `backend/alembic/script.py.mako` - Alembic revision template for future migrations.
- `backend/alembic/versions/20260303_01_ingest_deliveries.py` - Migration creating `prisoners` and `ingest_deliveries` with uniqueness + FK.
- `backend/app/models/ingest_delivery.py` - Delivery persistence model with Python 3.9-safe nullable typing.
- `backend/app/services/ingest_service.py` - Insert-first transactional replay guard and prisoner mutation logic.
- `backend/app/api/routes/ingest.py` - Route delegation to ingest service with DB session and source-IP wiring.
- `backend/tests/ingest/test_idempotency.py` - Migration, duplicate replay, and concurrent duplicate mutation guarantees.

## Decisions Made
- Used `delivery_id` insert-first behavior as the single replay gate before any prisoner mutation path executes.
- Kept duplicate submissions as successful responses (`200 duplicate_ignored`) to make forwarder retries deterministic and safe.
- Verified schema truth through migration-driven tests rather than model-only assumptions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Runtime lacked required migration dependencies**
- **Found during:** Task 1 RED verification
- **Issue:** Test execution failed with `ModuleNotFoundError: alembic` because dependencies were not installed in the local venv.
- **Fix:** Installed project dependencies with `backend/.venv/bin/pip install '.[dev]'`.
- **Files modified:** None (environment-only change)
- **Verification:** Task 1 and Task 2 idempotency tests executed successfully in the venv.
- **Committed in:** N/A (environment setup)

**2. [Rule 3 - Blocking] Editable install unsupported by current pip**
- **Found during:** Task 1 setup
- **Issue:** `pip` version in the venv could not perform editable installs from `pyproject.toml`.
- **Fix:** Switched to non-editable local install mode for dependency bootstrap.
- **Files modified:** None
- **Verification:** Package and dependencies installed successfully; test suite passed.
- **Committed in:** N/A (environment setup)

**3. [Rule 1 - Bug] SQLAlchemy annotation failure on Python 3.9**
- **Found during:** Task 1 RED verification
- **Issue:** `Mapped[int | None]` in `IngestDelivery` caused SQLAlchemy mapped annotation resolution errors on Python 3.9.
- **Fix:** Replaced union operator annotation with `Optional[int]`.
- **Files modified:** `backend/app/models/ingest_delivery.py`
- **Verification:** Migration/idempotency tests imported models and passed.
- **Committed in:** `60a6013`

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** All fixes were required to execute planned scope and did not introduce scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Replay-safe ingest persistence contract is now in place and validated.
- Ready for Plan 01-04 rate limiting and heartbeat liveness controls.

