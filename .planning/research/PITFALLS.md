# Pitfalls Research

**Domain:** Gamified threat-intelligence honeypot dashboard (Cowrie -> FastAPI -> React)
**Researched:** 2026-03-03
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Honeypot Sensor Becomes a Pivot Point

**What goes wrong:**
The Cowrie host is treated like a normal app server, attackers achieve deeper host access, and the sensor becomes a launchpad into other infrastructure.

**Why it happens:**
Teams focus on capturing attack traffic quickly and skip strict host isolation, non-root execution, and egress controls.

**How to avoid:**
Run Cowrie as a dedicated non-root user, isolate the sensor in its own network segment/VPS, restrict outbound connectivity to only required destinations, and continuously harden/patch the host image.

**Warning signs:**
Unexpected outbound traffic from the sensor, process execution outside Cowrie/Twisted, unexplained firewall/NAT rule drift, or host-level auth attempts unrelated to honeypot operation.

**Phase to address:**
Phase 1 - Sensor hardening and secure ingress foundation.

---

### Pitfall 2: Ingest Trust Boundary Collapse

**What goes wrong:**
Untrusted payloads from the forwarder are treated as trusted events, allowing spoofed records, malformed data, and event poisoning to enter the pipeline.

**Why it happens:**
API-key auth is added, but teams skip strict schema validation, replay protection, and source-IP enforcement under launch pressure.

**How to avoid:**
Enforce API key + allowlist + strict request schema + size limits + timestamp skew checks + idempotency keys; reject unknown fields and malformed events at the boundary.

**Warning signs:**
Sudden spikes in rejected/odd event shapes, repeated duplicate sessions, growing dead-letter queue, or impossible event sequences for a single session.

**Phase to address:**
Phase 1 - Secure ingestion and idempotency controls.

---

### Pitfall 3: Event Model Drift Between Cowrie and Dashboard

**What goes wrong:**
The dashboard and enrichment workers assume stable event fields, but Cowrie event types/attributes vary, causing dropped parsing paths and broken UI states.

**Why it happens:**
Developers map only a small subset of events (happy path) and skip contract tests against real/recorded Cowrie payload diversity.

**How to avoid:**
Define versioned internal event contracts, keep raw event payloads for replay tests, validate parser coverage across key Cowrie event families, and treat unknown event types as first-class telemetry.

**Warning signs:**
Increase in "unknown event" counters, null-heavy prisoner detail panes, parsing exception bursts after Cowrie updates, or mismatched session timelines.

**Phase to address:**
Phase 2 - Canonical event schema and parser reliability.

---

### Pitfall 4: Enrichment APIs Become a Reliability Bottleneck

**What goes wrong:**
Threat-intel/geolocation lookups are performed inline or without quota-aware controls, causing ingest slowdown, timeouts, and cascading failures.

**Why it happens:**
External enrichment is treated as "cheap metadata" instead of a rate-limited dependency with variable latency and failure modes.

**How to avoid:**
Decouple enrichment from ingest, queue and backoff retries, enforce per-provider budgets, cache by IP/time window, honor `429` and `Retry-After`, and degrade gracefully when providers fail.

**Warning signs:**
Rising ingest latency when enrichment latency rises, frequent `429` responses, retry storms, stale enrichment backlog, or event loop saturation.

**Phase to address:**
Phase 3 - Asynchronous enrichment orchestration and failure isolation.

---

### Pitfall 5: Real-Time Stream Works in Dev but Fails in Production Topology

**What goes wrong:**
In-memory WebSocket connection/broadcast state works on one process, then breaks under multi-process/multi-instance deployment with message loss and inconsistent client views.

**Why it happens:**
Teams copy minimal WebSocket examples and defer brokered fan-out design until after deployment.

**How to avoid:**
Use process-external pub/sub for broadcast fan-out, track connection lifecycle robustly, add per-client backpressure handling, and load-test with realistic concurrent viewers.

**Warning signs:**
Clients connected to different instances showing divergent stats, periodic missed updates after deploy/scale events, and memory growth from slow/stuck connections.

**Phase to address:**
Phase 4 - Production-grade WebSocket transport and fan-out.

---

### Pitfall 6: Attacker-Controlled Strings Leak into UI/Logs

**What goes wrong:**
Command inputs, usernames, banners, or payload fragments are rendered/logged unsafely, enabling XSS-like display issues, log injection, and analyst confusion.

**Why it happens:**
Threat data is mistaken for "already-safe telemetry" and is passed through UI and logs without normalization/sanitization policy.

**How to avoid:**
Treat all attacker-origin fields as untrusted; sanitize and encode for each sink (JSON logs, SQL, HTML), strip control characters, and mask sensitive attributes before client broadcast.

**Warning signs:**
Broken UI rows from escape/control sequences, malformed log lines, parser breakage in downstream log tools, or unexpected script-like content appearing in analyst views.

**Phase to address:**
Phase 2 - Data sanitization policy and output encoding hardening.

---

### Pitfall 7: Data Model Locks and Retention Debt Accumulate Silently

**What goes wrong:**
Large mutable JSON blobs and missing retention jobs create lock contention, slow queries, and storage growth that degrade real-time UX.

**Why it happens:**
JSON fields are used as a convenience for all evolving attributes, while query/index strategy and purge cadence are postponed.

**How to avoid:**
Use `jsonb` intentionally with targeted indexes, keep JSON documents bounded, split hot mutable fields into relational columns where needed, and enforce automated retention for prisoner/idempotency tables.

**Warning signs:**
Increasing write latency, lock wait spikes during updates, growing table/index bloat, and dashboard refresh stutter during peak ingest.

**Phase to address:**
Phase 3 - Persistence performance tuning and retention automation.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep all attacker/session detail in one large mutable JSON object | Fast initial schema design | Row lock contention, hard indexing, expensive migrations | MVP only, with explicit size limits and migration plan |
| Broadcast directly from app memory without external broker | Minimal setup and low latency in dev | Multi-instance inconsistency and dropped events | Never for production real-time dashboards |
| Inline enrichment calls in ingest endpoint | Fewer moving parts | Ingest latency coupling to third-party APIs, cascading failures | Never |
| Defer IP masking rules to frontend only | Quick demo output | Potential sensitive data leakage through APIs/logs | Never |
| Skip replay/idempotency store initially | Faster forwarder integration | Duplicate attackers, inflated metrics, noisy alerts | MVP only for local prototype with disposable data |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Cowrie -> forwarder | Assuming every event type has identical fields | Parse by event family, preserve raw payload, and validate required attributes per event |
| Forwarder -> FastAPI ingest | Trusting API key alone | Combine API key auth, source allowlist, schema validation, replay/idempotency controls |
| FastAPI -> WebSocket clients | Using one-process in-memory connection list for production | Use broker-backed fan-out and connection health/backpressure controls |
| Backend -> threat-intel APIs | Ignoring quota headers and retry guidance | Honor `429` + `Retry-After`, cache lookups, apply jittered backoff |
| Backend -> Postgres | Storing large, frequently updated documents with no index strategy | Use bounded `jsonb`, targeted indexes, and normalized hot fields |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous enrichment in ingest path | Ingest p95/p99 latency tracks third-party API latency | Queue enrichment asynchronously and batch/cache calls | Usually visible after sustained burst traffic or provider slowness |
| Per-event full-table/stat recomputation | CPU spikes and delayed `stats_update` pushes | Maintain incremental counters/materialized summaries | Commonly breaks around thousands of daily events on small instances |
| Unbounded in-memory WebSocket queues | Rising memory, delayed frames for slower clients | Apply per-client queue caps/drop policy and heartbeat disconnects | Typically with tens to hundreds of concurrent viewers |
| Overuse of unindexed JSON predicates | Slow detail/search queries and lock contention | Add focused `jsonb` indexes and flatten hot query paths | Often after dataset reaches multi-week retention |
| Frontend rerendering every stream event globally | Janky animation and input lag | Use event batching, selective state updates, and render virtualization | Around 20-50 visible animated entities with frequent updates |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Running Cowrie with excessive host privileges | Sensor compromise can impact host/network | Dedicated non-root runtime, network isolation, least privilege |
| Treating threat-intel API keys as client-safe | Credential exposure and abuse of quota/billing | Keep keys server-side only; never expose in frontend bundles |
| Rendering attacker-controlled strings without sink-specific encoding | UI defacement/XSS-like behavior, log corruption | Sanitize control chars and encode per output sink |
| Accepting client-originated WebSocket control/data events in public dashboard | Unauthorized state mutation or abuse | Keep client channel read-only; reject custom inbound actions |
| Logging full unmasked IPs in publicly accessible channels | Privacy/reputation and potential policy risk | Mask by default in UI/log streams; gate raw access behind admin controls |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Over-gamifying attack activity with weak context | Users perceive it as novelty, not intelligence | Pair every visual event with explainable threat context and confidence cues |
| Stats that update with no provenance window | Analysts lose trust in metrics | Show time windows, source labels, and last-update timestamps |
| No clear distinction between "new", "updated", and "enriched" states | Confusing event lifecycle comprehension | Use explicit state chips/timestamps in detail pane |
| Visual noise from every low-value event | Important patterns are buried | Prioritize high-signal events and allow filtering by severity/source |
| Desktop-only interaction assumptions | Poor mobile/tablet review experience | Mobile-first interaction targets with progressive detail layout |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Ingest API:** Often missing replay/idempotency enforcement — verify duplicate forwarder replays do not create duplicate prisoner/session records.
- [ ] **Enrichment pipeline:** Often missing quota-aware backoff — verify controlled behavior under forced `429` and provider timeout scenarios.
- [ ] **WebSocket feed:** Often missing multi-instance consistency — verify identical updates across clients connected to different app instances.
- [ ] **Threat data rendering:** Often missing output sanitization policy — verify control characters and HTML/script-like payloads render as inert text.
- [ ] **Retention jobs:** Often missing operational scheduling — verify automated purge for >30-day prisoner data and >7-day idempotency artifacts.
- [ ] **Security boundaries:** Often missing end-to-end secret exposure checks — verify no API keys or raw sensitive values leak to frontend/network logs.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Sensor pivot risk discovered | HIGH | Isolate and rebuild sensor host from clean image, rotate all credentials/keys, re-verify firewall and outbound rules, and re-enable traffic in staged mode |
| Ingest trust boundary failure | HIGH | Freeze ingest, quarantine suspicious payload window, patch validators/idempotency checks, replay only verified dead-letter batches |
| Event model drift causing parse failures | MEDIUM | Hotfix parser with safe fallback, backfill from raw event archive, add contract tests for missed event shapes |
| Enrichment dependency meltdown | MEDIUM | Disable non-critical enrichers via feature flag, drain queue with rate-aware worker limits, re-enable providers gradually with cache warmup |
| WebSocket fan-out inconsistency | MEDIUM | Switch to broker-backed broadcast path, force reconnect clients, replay latest snapshot state to all subscribers |
| Unsanitized attacker content exposure | HIGH | Disable affected views, sanitize stored/display paths, purge/repair poisoned logs where feasible, add sink-specific encoding tests |
| Storage/lock contention from data model | MEDIUM | Add targeted indexes, split hot fields, schedule retention cleanup, and run phased backfill/migration off-peak |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Honeypot sensor pivot risk | Phase 1 - Sensor hardening and secure ingress | Host hardening checklist passed, egress policy test passed, no root Cowrie process in runtime audit |
| Ingest trust boundary collapse | Phase 1 - Secure ingestion and idempotency controls | Replay/forgery test suite proves invalid payload rejection and duplicate suppression |
| Event model drift | Phase 2 - Canonical event schema and parser reliability | Contract tests pass across captured Cowrie event corpus; unknown-event metric remains within threshold |
| Attacker-controlled string injection | Phase 2 - Data sanitization and encoding hardening | Security tests prove inert rendering/logging for hostile payload corpus |
| Enrichment bottleneck and quota collapse | Phase 3 - Async enrichment orchestration | Load tests show ingest SLO unaffected by enrichment provider failures/`429` responses |
| Data-model lock and retention debt | Phase 3 - Persistence tuning and retention automation | DB latency/lock metrics stay within SLO; scheduled retention jobs run and are auditable |
| WebSocket production inconsistency | Phase 4 - Brokered real-time transport | Multi-instance chaos test shows consistent event delivery and bounded client lag |
| Gamification-over-clarity UX failure | Phase 5 - Intelligence-first UX and trust cues | Usability review confirms users can explain event meaning and lifecycle without facilitator help |

## Sources

- https://docs.cowrie.org/en/latest/INSTALL.html
- https://docs.cowrie.org/en/latest/OUTPUT.html
- https://fastapi.tiangolo.com/advanced/websockets/
- https://www.postgresql.org/docs/current/datatype-json.html
- https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- https://docs.abuseipdb.com/
- /Users/rob/Documents/OT Apps/Holding Cell/.planning/PROJECT.md

---
*Pitfalls research for: Gamified threat-intelligence honeypot dashboard (Cowrie -> FastAPI -> React)*
*Researched: 2026-03-03*
