# Roadmap: The Holding Cell

## Overview

This roadmap delivers the v1 live intelligence loop in dependency order: trust the ingest boundary first, build canonical data, add asynchronous enrichment, stream updates reliably, then deliver the responsive dashboard experience on top.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Trusted Ingest Boundary** - Secure, validated, replay-safe intake for forwarder traffic.
- [ ] **Phase 2: Canonical Prisoner Data** - Durable attacker model, query surfaces, and retention hygiene.
- [ ] **Phase 3: Async Threat Enrichment** - Non-blocking intelligence enrichment with graceful failure handling.
- [ ] **Phase 4: Realtime Event Stream** - Reliable websocket delivery for prisoner lifecycle and stats updates.
- [ ] **Phase 5: Responsive Analyst Dashboard** - Interactive, safe, and responsive UI for live threat inspection.

## Phase Details

### Phase 1: Trusted Ingest Boundary
**Goal**: Operator can ingest Cowrie telemetry through a hardened API boundary that resists abuse and preserves service availability.
**Depends on**: Nothing (first phase)
**Requirements**: ING-01, ING-02, ING-03, ING-04, ING-05, SEC-03
**Success Criteria** (what must be TRUE):
  1. Operator can submit ingest payloads only from allowlisted source IPs with valid API key authentication.
  2. Operator sees invalid payloads rejected with safe schema validation errors when size and field constraints are violated.
  3. Operator can resend the same `delivery_id` without creating duplicate prisoner records.
  4. Operator receives `429` responses with retry guidance under burst traffic while ingest remains available.
  5. Operator can post heartbeats to confirm forwarder liveness, and browser clients from non-approved origins are blocked by CORS/CSP policy.
**Plans**: 5 plans
Plans:
- [x] 01-01-PLAN.md — Shared trusted-forwarder auth + source-IP allowlist boundary.
- [x] 01-02-PLAN.md — Strict ingest/heartbeat schema validation and payload-size defenses.
- [x] 01-03-PLAN.md — Delivery idempotency persistence and transactional replay-safe ingest flow.
- [ ] 01-04-PLAN.md — Burst-rate limiting contract and heartbeat liveness monitoring.
- [ ] 01-05-PLAN.md — Approved-origin CORS/WebSocket/CSP alignment and security tests.

### Phase 2: Canonical Prisoner Data
**Goal**: Users can reliably inspect canonical attacker records and query them predictably from persisted storage.
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):
  1. User sees one canonical prisoner per source IP, with repeat attacks reflected in `attempt_count`.
  2. User can open a prisoner and inspect persisted credentials, commands, downloads, and protocol history.
  3. User can browse prisoner lists with pagination, deterministic sorting, and country filtering.
  4. Operator can verify automatic purging of prisoners older than 30 days and idempotency records older than 7 days.
**Plans**: TBD

### Phase 3: Async Threat Enrichment
**Goal**: Users receive useful threat context without making ingest latency or availability depend on external providers.
**Depends on**: Phase 2
**Requirements**: INTL-01, INTL-02, INTL-03, INTL-04
**Success Criteria** (what must be TRUE):
  1. User sees geo and reputation enrichment attached to new prisoners when providers succeed.
  2. User still sees newly ingested prisoners when providers fail, with status clearly shown as `pending`, `partial`, or `failed`.
  3. User receives deferred enrichment updates after initial creation without losing initial prisoner visibility.
  4. Operator can sustain flood conditions without exhausting enrichment quota because excess work is deferred to a controlled queue.
**Plans**: TBD

### Phase 4: Realtime Event Stream
**Goal**: Users get accurate live prisoner and aggregate updates over reconnect-safe websocket channels.
**Depends on**: Phase 3
**Requirements**: RT-01, RT-02, RT-03, SEC-04
**Success Criteria** (what must be TRUE):
  1. User sees new prisoners appear in the cell within seconds via `new_prisoner` events.
  2. User sees repeat-offender and enrichment lifecycle changes reflected live via `prisoner_updated` and `prisoner_enriched`.
  3. User sees aggregate stats update through `stats_update`, and reconnect restores current state correctly.
  4. User can only consume read-only websocket updates; client-emitted custom events are ignored by the server.
**Plans**: TBD

### Phase 5: Responsive Analyst Dashboard
**Goal**: Users can operate a responsive, filterable, and safe dashboard to inspect hostile activity in real time.
**Depends on**: Phase 4
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05, SEC-01, SEC-02
**Success Criteria** (what must be TRUE):
  1. User can use header, cell, detail pane, and stats bar across desktop and tablet/mobile fallback layouts.
  2. User can select a prisoner to inspect attack summary, threat-intel context, and activity timestamps in the detail pane.
  3. User can identify threat severity from color and attempt prominence, and see that encoding update when enrichment arrives.
  4. User can narrow visible prisoners using at least one operational filter (time window and/or country/protocol).
  5. User sees clear live/reconnecting/offline connection state while attacker-controlled strings are safely rendered and source IPs remain masked by default.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Trusted Ingest Boundary | 3/5 | In Progress | - |
| 2. Canonical Prisoner Data | 0/TBD | Not started | - |
| 3. Async Threat Enrichment | 0/TBD | Not started | - |
| 4. Realtime Event Stream | 0/TBD | Not started | - |
| 5. Responsive Analyst Dashboard | 0/TBD | Not started | - |
