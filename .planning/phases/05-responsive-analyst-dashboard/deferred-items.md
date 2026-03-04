# Deferred Items

Items discovered during plan execution but intentionally deferred because they are out of scope.

## 2026-03-04 - Plan 05-06

- `frontend/src/features/dashboard/state/realtime-reconcile.ts` has pre-existing TypeScript union narrowing errors that fail `npm run build`:
  - payload passed to `reconcileRealtimePrisonerPayload` is not narrowed to `DashboardPrisonerRealtimePayload`.
  - `payload.prisoners` access on union payload without event narrowing.
  - stats updater path accepts union payload where `DashboardStatsUpdatePayload` is expected.
- Not fixed in this plan because 05-06 scope is dashboard presentation components + focused row/detail tests.
