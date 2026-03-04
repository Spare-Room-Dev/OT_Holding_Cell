# Milestones

## v1.0 MVP (Shipped: 2026-03-04)

**Phases completed:** 5 phases, 26 plans, 52 tasks
**Timeline:** 2026-03-03 -> 2026-03-04
**Git range:** `b5cbd9b` (`feat(01-01)`) -> `b6d20c4` (`docs(v1.0)`)

**Key accomplishments:**
- Hardened ingest boundary with API-key auth, source-IP allowlisting, strict schema validation, replay-safe idempotency, and endpoint-scoped throttling.
- Established canonical prisoner persistence with deterministic list/detail query APIs and retention rollup/purge behavior.
- Delivered asynchronous threat enrichment with durable queueing, bounded retry/defer semantics, and operator queue-health visibility.
- Implemented reconnect-safe realtime websocket sync and post-commit lifecycle event publishing for prisoner and stats updates.
- Shipped responsive analyst dashboard with typed contracts, safe attacker-string rendering, masked-IP defaults, filters, and connection-state UX.

### Known Gaps / Tech Debt Accepted At Ship

- `DATA-03` remains partially externally verified: local retention script/tests pass, but deployed Render cron proof requires human/environment validation.
- Frontend runtime endpoint resolution and CSP topology can diverge in split-domain deployments without explicit alignment.
- Playwright dashboard coverage currently validates mocked REST/WS flows; full live backend browser wiring remains to be added.

---
