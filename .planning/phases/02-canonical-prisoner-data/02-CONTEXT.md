# Phase 2: Canonical Prisoner Data - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver durable canonical prisoner records and predictable query access from persisted storage, including repeat-attempt aggregation, prisoner detail inspection, deterministic pagination/sorting/country filtering, and automatic data retention hygiene.

</domain>

<decisions>
## Implementation Decisions

### Canonical Identity Model
- Canonical prisoner identity is keyed by `source_ip` (not `source_ip + protocol`).
- Protocol behavior is preserved as rich protocol history on the single prisoner record (per-protocol first/last seen and attempts).
- Existing phase-1 protocol-split rows should be merged into source-IP canonical rows during transition.
- `attempt_count` increments once per accepted non-duplicate ingest delivery.

### Query Surface Contract
- Prisoner list pagination uses cursor pagination.
- Default list sort is newest activity first (`last_seen desc`) with a stable deterministic tie-breaker.
- Country filtering includes an explicit `unknown` option for unresolved geo records.
- List responses stay lightweight (summary rows), with full activity retrieved from a prisoner detail endpoint.

### Persisted Detail History
- Credential history is stored as masked entry records with timestamp/protocol context.
- Commands and downloads are retained as chronological append-only histories with fixed caps.
- When caps are reached, oldest entries are dropped first.
- Detail responses organize data as separate sections (protocol history, credentials, commands, downloads), not a unified mixed timeline.
- Cap sizing should use a balanced profile for v1 (neither minimal nor maximal).

### Retention and Lifecycle
- Automatic retention runs as a daily scheduled job.
- Expired prisoner records are hard-deleted at 30 days.
- `ingest_deliveries` records are strictly purged at 7 days.
- Even with hard-delete detail retention, lifetime aggregate rollups should be preserved for headline stats (for example total breaches and breaches by country).

### Claude's Discretion
- Exact cap numbers for credentials/commands/downloads under the balanced profile.
- Cursor token structure/encoding details.
- Scheduler mechanism and operational wiring for daily cleanup execution.
- Exact shape of aggregate rollup storage used to preserve lifetime totals.

</decisions>

<specifics>
## Specific Ideas

- Retention should not break high-level stats visibility; totals like "Total Breaches" and "Breaches by Country" should remain available even when detailed prisoner rows age out.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/prisoner.py`: Existing prisoner model and uniqueness constraints are the base starting point for canonical identity changes.
- `backend/app/models/ingest_delivery.py`: Existing idempotency table supports replay-safe delivery tracking and 7-day retention target.
- `backend/app/services/ingest_service.py`: Transactional ingest mutation path already centralizes duplicate detection and prisoner updates.
- `backend/tests/ingest/test_idempotency.py`: Strong replay-safety tests can be extended for canonical merge and attempt-count behavior.

### Established Patterns
- Delivery insert-first idempotency semantics are established and should remain intact.
- Strict request validation with bounded list sizes is already in place (`backend/app/schemas/ingest.py`).
- Persistence stack is SQLAlchemy + Alembic migrations with test-first coverage around boundary behavior.
- Current API routing pattern is FastAPI route modules under `backend/app/api/routes`.

### Integration Points
- Canonical data changes connect through the ingest service mutation flow and prisoner/ingest-delivery models.
- New query endpoints should follow existing API route organization and DB session dependency patterns.
- Retention scheduling and rollup updates should integrate with backend persistence and operational health surfaces.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 2 boundary.

</deferred>

---

*Phase: 02-canonical-prisoner-data*
*Context gathered: 2026-03-03*
