# Requirements: The Holding Cell

**Defined:** 2026-03-03
**Core Value:** Turn raw honeypot attack traffic into an immediate, understandable, real-time visual intelligence feed.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Ingest

- [x] **ING-01**: Operator can receive Cowrie attack session payloads through `POST /api/ingest` using API-key authentication and source-IP allowlisting.
- [x] **ING-02**: Operator can ingest payloads only when payload schema is valid (including bounded list sizes and field length limits) and reject invalid requests safely.
- [x] **ING-03**: Operator can submit duplicate deliveries with the same `delivery_id` and have the backend ignore replays without creating duplicate attacker records.
- [x] **ING-04**: Operator can keep ingest available during burst traffic using endpoint rate limiting and return `429` with retry guidance when limits are exceeded.
- [x] **ING-05**: Operator can verify forwarder liveness through `POST /api/heartbeat` and detect missed heartbeats within the configured warning window.

### Data

- [x] **DATA-01**: User can see one canonical prisoner record per unique source IP with repeat attacks aggregated into `attempt_count`.
- [x] **DATA-02**: User can inspect credentials, commands, downloads, and protocol history for a prisoner from persisted backend data.
- [x] **DATA-03**: Operator can automatically purge prisoners older than 30 days and idempotency delivery records older than 7 days.
- [ ] **DATA-04**: User can request paginated prisoner lists with deterministic sorting and country filtering.

### Intel

- [ ] **INTL-01**: User can view geo and reputation enrichment for new IPs when provider calls succeed.
- [ ] **INTL-02**: User can still view newly ingested prisoners when enrichment providers fail, with enrichment status shown as `pending`, `partial`, or `failed`.
- [ ] **INTL-03**: User can receive deferred enrichment updates after initial prisoner creation without losing initial event visibility.
- [ ] **INTL-04**: Operator can prevent enrichment quota exhaustion during floods by deferring excess enrichment workload to a controlled background queue.

### Realtime

- [ ] **RT-01**: User can see a new prisoner appear in the cell within seconds of ingest via `new_prisoner` events.
- [ ] **RT-02**: User can see repeat-offender updates and enrichment completions reflected live via `prisoner_updated` and `prisoner_enriched` events.
- [ ] **RT-03**: User can see live aggregate metrics update through `stats_update` events and recover correctly after reconnect.

### Dashboard

- [ ] **UI-01**: User can view a responsive dashboard with header, cell, detail pane, and stats bar across desktop and tablet/mobile fallback layouts.
- [ ] **UI-02**: User can click a prisoner to inspect attack summary, threat-intel context, and activity timestamps in the detail pane.
- [ ] **UI-03**: User can identify threat severity from prisoner visual encoding (color + attempt prominence) that updates when enrichment arrives.
- [ ] **UI-04**: User can apply at least one operational filter (time window and/or country/protocol) to narrow visible prisoners.
- [ ] **UI-05**: User can understand connection health through clear live/reconnecting/offline status indicators.

### Security

- [ ] **SEC-01**: User can view attacker strings safely because attacker-controlled fields are rendered as text and sanitized before display.
- [ ] **SEC-02**: User can view masked source IPs by default in public-facing views while backend storage retains full IPs.
- [x] **SEC-03**: Operator can enforce frontend CSP/CORS restrictions so only approved frontend origins can connect to backend APIs/WebSocket.
- [ ] **SEC-04**: User can interact with a read-only WebSocket channel where client-emitted custom events are not processed by the server.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Intelligence

- **INTX-01**: User can view intent scoring that classifies behavior (for example opportunistic scanner vs suspicious actor).
- **INTX-02**: User can replay notable attack sessions with deterministic timeline controls.
- **INTX-03**: User can view campaign-level clustering of related attacker behavior across sessions.

### Integrations

- **INTG-01**: Operator can deliver alert/webhook notifications to external tools (Slack, Discord, SIEM).
- **INTG-02**: Operator can ingest from multiple honeypot sensors through a stable adapter interface.

### Admin

- **ADMIN-01**: Authorized analyst can access private unmasked IOC detail in a restricted admin workspace.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Pixel-art walk-cycle prisoner sprites | Visual polish deferred until core ingest-to-UI loop is proven |
| OT/ICS themed control-room framing | Styling enhancement deferred to protect v1 delivery |
| Public unmasked IP display | Conflicts with privacy-safe public demo posture |
| Full SOC case management workflow | Too broad for initial validation of core dashboard value |
| PDF export of records | Not required to validate real-time intelligence use case |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ING-01 | Phase 1 | Complete |
| ING-02 | Phase 1 | Complete |
| ING-03 | Phase 1 | Complete |
| ING-04 | Phase 1 | Complete |
| ING-05 | Phase 1 | Complete |
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 2 | Pending |
| INTL-01 | Phase 3 | Pending |
| INTL-02 | Phase 3 | Pending |
| INTL-03 | Phase 3 | Pending |
| INTL-04 | Phase 3 | Pending |
| RT-01 | Phase 4 | Pending |
| RT-02 | Phase 4 | Pending |
| RT-03 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 5 | Pending |
| UI-05 | Phase 5 | Pending |
| SEC-01 | Phase 5 | Pending |
| SEC-02 | Phase 5 | Pending |
| SEC-03 | Phase 1 | Complete |
| SEC-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after roadmap mapping*
