# Architecture Research

**Domain:** Gamified threat-intelligence honeypot dashboard
**Researched:** 2026-03-03
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Edge Collection Layer                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Cowrie Node  │  │  Forwarder   │  │ Retry/DLQ    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │              │
├─────────┴─────────────────┴─────────────────┴───────────────┤
│                  Application Service Layer                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │ FastAPI Core (ingest, idempotency, enrichment, WS) │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                   Data + Intelligence Layer                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │PostgreSQL│  │ Geo/ASN  │  │ Threat   │                 │
│  │ (Render) │  │ Provider │  │ Intel API│                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Cowrie Node | Emit raw SSH/Telnet attack events | Cowrie sensor with JSON output |
| Forwarder | Normalize, sign, and submit payloads outbound-only | Python daemon with retry, heartbeat, dead-letter file |
| Ingest API | Authenticate, validate schema, apply rate limits | FastAPI route with API-key auth + pydantic validation |
| Idempotency Guard | Prevent duplicate processing per event key | PostgreSQL idempotency table + unique constraint |
| Session Store | Persist attacker/session records for live and detail views | Async PostgreSQL writes with indexed attacker/session keys |
| Enrichment Worker | Attach geo/threat context without blocking ingest | Async background task queue/worker in FastAPI process |
| Realtime Broadcaster | Fan out canonical events to UI clients | WebSocket manager publishing `new_prisoner` and updates |
| React Dashboard | Render cell view, detail pane, stats bar, masked IPs | Vite + React + TS + event-driven client store |

## Recommended Project Structure

```
src/
├── forwarder/          # Cowrie egress client running on VPS
│   ├── adapters/       # Cowrie event parsing and normalization
│   └── sender.py       # Authenticated delivery + retry/DLQ handling
├── backend/            # FastAPI service on Render
│   ├── api/            # Ingest and websocket transport boundaries
│   └── domain/         # Idempotency, enrichment, retention, stats logic
├── frontend/           # Vite React dashboard on Vercel
│   ├── features/       # Cell scene, inspector panel, stats bar modules
│   └── state/          # Event store and websocket reducers/selectors
├── shared/             # Event contracts and payload schemas
└── infra/              # Deployment and environment wiring
```

### Structure Rationale

- **forwarder/:** Isolates hostile-input parsing from backend trust boundary; build this first so backend contracts are tested with realistic payloads.
- **backend/:** Owns source-of-truth business rules and persistence; build second because all downstream realtime/UI behavior depends on canonical events here.
- **frontend/:** Depends on stable websocket contracts; build third once `new_prisoner`, update, and stats events are available.
- **shared/:** Keeps event schema drift low across forwarder/backend/frontend; define early and version strictly.
- **infra/:** Codifies deployment constraints (Vultr, Render, Vercel) and should track every stage as components are introduced.

## Architectural Patterns

### Pattern 1: Ingest Fast, Enrich Async

**What:** Accept and persist minimally complete attacker records first, then run enrichment in a separate path.
**When to use:** Any time third-party intel APIs are latency-variable or unreliable.
**Trade-offs:** Better ingest availability and lower p95 latency, but introduces eventual consistency in detail panels.

**Example:**
```typescript
async function handleIngest(event: CowrieEvent) {
  const prisoner = await repository.insertBaseRecord(event);
  queue.enqueue({ type: "ENRICH_PRISONER", prisonerId: prisoner.id });
  ws.publish("new_prisoner", prisoner);
}
```

### Pattern 2: Contract-First Event Streaming

**What:** Treat websocket payloads as versioned contracts shared by backend and frontend.
**When to use:** Realtime UIs where multiple producers can evolve at different speeds.
**Trade-offs:** Initial schema discipline overhead, but fewer runtime regressions and easier phased rollout.

**Example:**
```typescript
type DashboardEvent =
  | { type: "new_prisoner"; payload: PrisonerSummary; v: 1 }
  | { type: "prisoner_enriched"; payload: PrisonerDetail; v: 1 }
  | { type: "stats_update"; payload: DashboardStats; v: 1 };
```

### Pattern 3: Security Boundary Segmentation

**What:** Separate untrusted ingest edge, trusted processing core, and public read-only presentation.
**When to use:** Systems that ingest attacker-controlled input and expose public dashboards.
**Trade-offs:** More explicit interfaces and deployment constraints, but significantly lower blast radius.

## Data Flow

### Request Flow

```
[Cowrie Attack Event]
    ↓
[Forwarder] → [Ingest API] → [Domain Service] → [PostgreSQL]
    ↓              ↓              ↓                 ↓
[ACK/Retry] ← [Validation] ← [Enrichment Job] ← [Persisted Record]
```

### State Management

```
[Client Event Store]
    ↓ (subscribe)
[React Components] ←→ [WS Event Handlers] → [Reducers] → [Client Event Store]
```

### Key Data Flows

1. **Live ingest to prisoner creation:** Cowrie event -> forwarder -> authenticated ingest -> idempotent insert -> `new_prisoner` broadcast. This is the first build milestone and unblocks all later work.
2. **Deferred enrichment to UI update:** Enrichment worker resolves geo/threat intel -> updates prisoner record -> emits `prisoner_enriched` + `stats_update`. This is a second-stage milestone that can ship after core ingest is stable.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Single FastAPI service + Postgres is sufficient; keep worker in-process and prioritize correctness/observability. |
| 1k-100k users | Split enrichment to dedicated worker process, add websocket fan-out optimization, add read-focused indexes and retention tuning. |
| 100k+ users | Introduce event bus for decoupled processing, shard hot tables/time partitions, and consider separate realtime gateway tier. |

### Scaling Priorities

1. **First bottleneck:** Enrichment API latency/backpressure; fix by queue isolation, concurrency caps, and retry budgets.
2. **Second bottleneck:** WebSocket broadcast fan-out and DB write contention; fix with event batching, connection partitioning, and table/index strategy.

## Anti-Patterns

### Anti-Pattern 1: Synchronous Enrichment in Ingest Path

**What people do:** Call geo/threat providers before storing a new attack event.
**Why it's wrong:** Ingest reliability becomes dependent on external APIs; dropped/late events during provider outages.
**Do this instead:** Persist minimal record first, enqueue enrichment asynchronously, and update clients later.

### Anti-Pattern 2: Frontend as Security Enforcement Layer

**What people do:** Mask IPs and sanitize fields only in UI while storing raw values unsafely.
**Why it's wrong:** Any alternate consumer path can leak sensitive or attacker-controlled data.
**Do this instead:** Enforce masking/sanitization policy server-side and expose only safe fields over websocket contracts.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Cowrie honeypot (Vultr) | Forwarder pulls/receives local Cowrie output, sends outbound HTTPS to backend | Keep inbound closed; heartbeat for sensor liveness |
| GeoIP/ASN provider | Async enrichment call with timeout + fallback fields | Never block ingest on provider failures |
| Threat-intel provider(s) | Async enrichment with per-provider circuit breaker behavior | Store partial enrichment with provenance and timestamp |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| forwarder ↔ backend ingest | HTTPS JSON API | Build first; defines trust boundary and payload contract |
| ingest/domain ↔ enrichment worker | Internal queue/job dispatch | Build second; decouples reliability from intel latency |
| backend websocket ↔ frontend state | Versioned event contracts | Build third; UI can evolve safely once contract is stable |

## Sources

- [/Users/rob/Documents/OT Apps/Holding Cell/.planning/PROJECT.md](/Users/rob/Documents/OT%20Apps/Holding%20Cell/.planning/PROJECT.md)
- [/Users/rob/.codex/agents/gsd-project-researcher.md](/Users/rob/.codex/agents/gsd-project-researcher.md)
- [/Users/rob/.codex/get-shit-done/templates/research-project/ARCHITECTURE.md](/Users/rob/.codex/get-shit-done/templates/research-project/ARCHITECTURE.md)

---
*Architecture research for: gamified threat-intelligence honeypot dashboard*
*Researched: 2026-03-03*
