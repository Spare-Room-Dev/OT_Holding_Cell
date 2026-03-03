# Phase 3: Async Threat Enrichment - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver non-blocking geo and reputation enrichment for newly ingested prisoners so ingest visibility is never delayed by external providers. This phase defines enrichment status behavior (`pending`, `partial`, `failed`), deferred processing under quota pressure, and how enrichment appears through existing query surfaces.

</domain>

<decisions>
## Implementation Decisions

### Enrichment Status Lifecycle
- New prisoners must be visible immediately with enrichment status `pending` and explicit placeholder/unknown intel values.
- `pending` must transition using timed failover with bounded retries; once exhausted, status becomes `failed` with reason metadata.
- If one provider succeeds and another fails, top-level status is `partial` while keeping successful intel.
- Status is not terminal: later successful retries auto-upgrade records from `pending`/`partial`/`failed` to the latest valid state.

### Intel Data Contract
- v1 enrichment guarantees country and ASN-level intel (building on existing country support).
- Reputation should be normalized to severity + confidence (not provider-raw-only values).
- Missing/unavailable intel values must be returned as explicit `null` values plus reason metadata (not omitted fields).
- Include minimal provenance/freshness metadata: provider identity and `last_enriched_at`.

### Deferred Update Visibility
- Enrichment status/intel summary must surface in prisoner list responses, with full intel in prisoner detail responses.
- Phase 3 guarantees that the next API fetch reflects latest enrichment outcomes after deferred processing.
- Include status plus update timestamp metadata so users can tell when enrichment last changed.

### Flood Queue and Quota Protection
- When provider quota is exceeded, excess enrichment work is deferred to a controlled queue; prisoner creation is never blocked.
- Deferred jobs process in FIFO order to avoid starvation.
- Queued jobs use bounded retries; exhausted jobs become `failed` with clear reason metadata.
- v1 must expose queue health signals for operations: queued/pending/failed counts and oldest pending age.

### Claude's Discretion
- Exact retry counts, retry spacing, and timeout window values.
- Concrete queue storage/execution mechanism and worker orchestration details.
- Final field naming/serialization shape for enrichment metadata (while preserving decisions above).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/ingest_service.py`: existing replay-safe ingest transaction and immediate prisoner create/update path is the anchor for non-blocking enrichment handoff.
- `backend/app/models/prisoner.py`: canonical prisoner record already contains `country_code` and aggregate counters, making it the natural home for enrichment status and intel fields.
- `backend/app/services/prisoner_query_service.py` and `backend/app/schemas/prisoners.py`: established list/detail response surfaces where enrichment visibility should be added.
- `backend/app/core/config.py`: established pattern for caps/limits via typed settings, suitable for enrichment retry/quota knobs.

### Established Patterns
- Ingest is delivery-id idempotent and transaction-first; enrichment must preserve this behavior and avoid duplicate side effects.
- Query responses are deterministic and summary-first for lists, sectioned for detail.
- Operational jobs already exist (`backend/scripts/run_retention.py`) with test-backed behavior, providing precedent for background workload management.

### Integration Points
- Enrichment kickoff connects after successful ingest mutation completion.
- Deferred processing connects to prisoner update persistence and then back into prisoner list/detail query outputs.
- Queue health and enrichment lifecycle state connect to existing backend operational monitoring surfaces and future realtime events in Phase 4.

</code_context>

<specifics>
## Specific Ideas

- Preserve immediate prisoner visibility as the top priority even under provider outage or quota pressure.
- Make partial/failure states explicit and understandable so users can trust data freshness and completeness.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 3 boundary.

</deferred>

---

*Phase: 03-async-threat-enrichment*
*Context gathered: 2026-03-03*
