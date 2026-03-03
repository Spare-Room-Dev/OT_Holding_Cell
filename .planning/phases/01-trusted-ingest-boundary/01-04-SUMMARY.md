---
phase: 01-trusted-ingest-boundary
plan: 04
subsystem: api
tags: [fastapi, rate-limit, heartbeat, alembic, liveness]
requires:
  - phase: 01-01
    provides: Shared trusted-forwarder auth and source-IP allowlist enforcement.
  - phase: 01-02
    provides: Strict ingest/heartbeat payload validation and safe error envelopes.
  - phase: 01-03
    provides: Replay-safe ingest persistence baseline.
provides:
  - Endpoint-specific deterministic rate limiting with explicit 429 retry headers.
  - Persistent forwarder heartbeat liveness state with stale-window detection.
  - Resilience test coverage for ingest throttling and heartbeat freshness.
affects: [01-05, ingest-availability, heartbeat-observability]
tech-stack:
  added: [sqlalchemy, alembic]
  patterns: [fixed-window-endpoint-limiter, persisted-heartbeat-liveness]
key-files:
  created:
    - backend/app/core/rate_limit.py
    - backend/app/models/forwarder_heartbeat.py
    - backend/alembic/versions/20260303_02_forwarder_heartbeat.py
    - backend/tests/ingest/test_rate_limit.py
    - backend/tests/heartbeat/test_liveness.py
  modified:
    - backend/app/core/config.py
    - backend/app/main.py
    - backend/app/api/routes/heartbeat.py
    - backend/app/services/heartbeat_service.py
    - backend/tests/conftest.py
key-decisions:
  - "Rate limits are endpoint-scoped so heartbeat and ingest quotas cannot starve each other."
  - "Heartbeat liveness is persisted by source_ip+protocol and returned with stale evaluation metadata."
patterns-established:
  - "429 contract includes Retry-After plus X-RateLimit headers for deterministic retry guidance."
  - "Heartbeat updates are upserted and evaluated against a configurable stale warning window."
requirements-completed: [ING-04, ING-05]
duration: 18 min
completed: 2026-03-03
---

# Phase 01 Plan 04: Trusted Ingest Boundary Summary

**Ingest and heartbeat endpoints now enforce deterministic endpoint-specific throttling, while heartbeat liveness is persisted and marked stale when warning windows are exceeded.**

## Performance

- **Duration:** 18 min
- **Tasks:** 2
- **Verification:** `25 passed` backend test suite

## Accomplishments
- Added reusable fixed-window endpoint limiter with deterministic 429 response body and retry headers.
- Enforced separate policy envelopes for ingest and heartbeat endpoints.
- Added persistent `forwarder_heartbeats` model + Alembic migration and service-layer liveness evaluation.
- Wired heartbeat route to persistence and stale-window response metadata.
- Added regression-safe fixtures so boundary tests run against migrated temporary databases.

## Task Commits
1. **Task 1 RED:** `b61d778` (`test(01-04): add failing endpoint rate-limit contract tests`)
2. **Task 1 GREEN:** `95e710f` (`feat(01-04): enforce endpoint rate-limit retry contracts`)
3. **Task 2 RED:** `16efb07` (`test(01-04): add failing heartbeat liveness persistence tests`)
4. **Task 2 GREEN:** `28352d6` (`feat(01-04): persist heartbeat liveness and stale-window detection`)
5. **Reconciliation fix:** `99f1f5a` (`fix(01-04): reconcile heartbeat service and migrated auth fixtures`)

## Deviations from Plan
- Concurrent background agent edits touched `heartbeat_service.py` during active execution. We reconciled to the newer interface (`record_heartbeat`) and re-verified all suites.
- Legacy auth tests required fixture modernization to run against latest migrations after heartbeat persistence was introduced.

## Verification
- `cd backend && .venv/bin/pytest tests/ingest/test_rate_limit.py tests/heartbeat/test_liveness.py -q` → `6 passed`
- `cd backend && .venv/bin/pytest -q` → `25 passed`

## Next Phase Readiness
- Ready for Plan 01-05 approved-origin CORS/WebSocket/CSP alignment.
