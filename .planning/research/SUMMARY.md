# Project Research Summary

**Project:** The Holding Cell
**Domain:** Gamified threat-intelligence honeypot dashboard (real-time ingest, enrichment, and live visualization)
**Researched:** 2026-03-03
**Confidence:** MEDIUM

## Executive Summary

The Holding Cell is a security product that turns raw Cowrie honeypot telemetry into a real-time, portfolio-safe intelligence experience. The research converges on a practical expert pattern: treat attacker input as hostile at every boundary, ingest quickly with strict validation and idempotency, persist canonical records, then enrich asynchronously and stream contract-validated updates to a React dashboard.

The recommended approach is a focused v1 with one sensor path and a hardened ingest-to-UI loop before advanced analytics. Stack choices are modern and well-supported: FastAPI + PostgreSQL + async Python services for reliable ingest/enrichment, and React + Vite + TypeScript for a responsive event-driven frontend. This architecture supports early delivery while preserving a clear scale path (queue isolation, brokered fan-out, and data model tuning).

The biggest risks are security boundary failures, schema drift, and reliability coupling to external enrichment APIs. Mitigation is explicit in the research: isolate and harden the sensor host, enforce strict ingest contracts with replay protection, sanitize attacker-controlled fields at server boundaries, and decouple enrichment from ingest with budgeted retries and graceful degradation.

## Key Findings

### Recommended Stack

The stack research is strong on version certainty and ecosystem fit. Python/FastAPI/PostgreSQL align with asynchronous ingest workloads and strict schema enforcement, while React/Vite/TypeScript give fast iteration and robust client-side contract handling for real-time dashboards.

**Core technologies:**
- **Python 3.13 + FastAPI 0.135.1:** ingest, auth boundary, and WebSocket transport with strong typing and low overhead.
- **PostgreSQL 18.x:** durable attacker/session storage with JSONB flexibility and indexing for evolving telemetry.
- **React 19 + Vite 7 + TypeScript 5.9:** event-driven UI with fast builds and safer contract evolution.
- **Pydantic + Zod:** dual-boundary validation to reject malformed attacker-controlled data before persistence/rendering.
- **SQLAlchemy + Alembic + psycopg:** consistent async persistence and migration discipline for production operations.

### Expected Features

Feature research is clear that launch success depends on trustworthy data flow and understandable live visibility, not feature breadth.

**Must have (table stakes):**
- Secure ingest with API auth, allowlist, schema validation, idempotency, and rate limits.
- Live attack stream plus drill-down session detail and operator-friendly filtering/stats.
- Async threat/geo enrichment with partial-failure tolerance.
- Safe public presentation defaults (masked IPs, sanitized output, read-only client behavior).

**Should have (competitive):**
- Prison-cell simulation tightly coupled to real event lifecycle.
- Narrative threat cards and early intent scoring to reduce analyst noise.
- Replay mode for notable sessions and operational storytelling.

**Defer (v2+):**
- Multi-sensor ingestion and adapter expansion beyond Cowrie.
- Private admin workspace with unmasked IOCs and richer RBAC workflows.
- Campaign clustering/graph analytics after sufficient data scale.

### Architecture Approach

Architecture findings reinforce a contract-first, boundary-segmented pipeline: forwarder normalizes and delivers outbound-only, FastAPI enforces trust boundaries and persistence, enrichment runs async, and frontend consumes versioned WebSocket events. This keeps v1 simple while preventing the most common reliability/security failures.

**Major components:**
1. **Edge collection (Cowrie + forwarder):** capture hostile traffic, normalize events, and deliver with retry/DLQ behavior.
2. **Application service (FastAPI core):** authenticate/validate ingest, enforce idempotency, persist canonical records, dispatch enrichment, and publish realtime events.
3. **Data/intelligence layer (Postgres + providers):** store source-of-truth telemetry and attach geo/threat context asynchronously.
4. **Presentation layer (React dashboard):** render cell scene, detail pane, and stats using versioned event contracts and masked/sanitized data.

### Critical Pitfalls

1. **Sensor pivot risk** — isolate and harden Cowrie host (non-root runtime, strict network segmentation, constrained egress).
2. **Ingest trust boundary collapse** — enforce strict schema validation, replay/idempotency controls, source allowlist, and size/skew limits.
3. **Event model drift** — version internal contracts, keep raw payload corpus, and run parser/contract tests across real Cowrie event diversity.
4. **Enrichment bottleneck coupling** — keep enrichment out of ingest path, honor quotas/retry semantics, and degrade gracefully.
5. **Production WebSocket inconsistency** — avoid single-process in-memory fan-out; use broker-backed broadcast and load-tested backpressure handling.

## Implications for Roadmap

Based on combined research, suggested phase structure:

### Phase 1: Hardened Sensor + Trusted Ingest Boundary
**Rationale:** Every downstream feature depends on trustworthy, abuse-resistant event intake.
**Delivers:** Sensor hardening baseline, forwarder auth path, strict schema validation, idempotency, rate limiting, and dead-letter/retry controls.
**Addresses:** Secure ingest, safe public posture foundation, and first telemetry reliability milestone.
**Avoids:** Sensor pivot and ingest trust-boundary failures.

### Phase 2: Canonical Event Model + Live Dashboard Core
**Rationale:** Product value appears once canonical events reliably reach a usable live UI.
**Delivers:** Stable event contracts, persistent attacker/session model, WebSocket lifecycle events, masked/sanitized dashboard with drill-down and core stats.
**Uses:** FastAPI + Postgres + React/Vite/TypeScript + Pydantic/Zod contract validation.
**Implements:** Contract-first streaming and security-boundary segmentation patterns.

### Phase 3: Async Enrichment + Data Hygiene Operations
**Rationale:** Context quality should improve without threatening ingest SLOs.
**Delivers:** Queue-backed enrichment with budgeted retries/backoff, provider-failure degradation, retention automation, and indexed query paths for sustained performance.
**Addresses:** Basic enrichment table stakes and reliable operational scaling to sustained traffic.
**Avoids:** Enrichment bottlenecks, retention debt, and lock/contention regression.

### Phase 4: Production Realtime Reliability
**Rationale:** Multi-instance deployment introduces correctness risks that dev topology hides.
**Delivers:** Brokered fan-out, connection lifecycle/backpressure controls, chaos/load tests, and cross-instance consistency guarantees.
**Addresses:** Real-time table stakes at production concurrency.
**Avoids:** Message divergence, dropped updates, and memory growth from slow clients.

### Phase 5: Intelligence Differentiators
**Rationale:** Differentiators should build on a proven reliable core, not precede it.
**Delivers:** Intent scoring lane, replay mode, narrative cards, and initial campaign-pattern grouping.
**Addresses:** Competitive differentiation and higher stakeholder comprehension.
**Avoids:** Over-gamification without trust context and premature analytics complexity.

### Phase Ordering Rationale

- Secure boundary controls and canonical contracts are prerequisite dependencies for enrichment, replay, and scoring.
- Architecture naturally groups into edge trust, core event pipeline, async intelligence, then transport scale hardening.
- This ordering directly neutralizes highest-severity pitfalls first (boundary/security/reliability), then layers differentiators.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** External enrichment provider strategy (quota behavior, caching TTLs, fallback design, cost envelope).
- **Phase 4:** Broker/fan-out design on selected hosting topology and realistic concurrent connection targets.
- **Phase 5:** Intent scoring methodology and replay UX validation thresholds to avoid noisy or low-trust outputs.

Phases with standard patterns (can usually skip research-phase):
- **Phase 1:** API hardening, allowlisting, idempotency, and replay protection are mature, well-documented patterns.
- **Phase 2:** Contract-first event modeling and React/FastAPI realtime integration are established and already well-specified in current research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions and compatibility were verified against official package registries/docs; recommendations are concrete and current. |
| Features | MEDIUM | Strong domain alignment and competitor grounding, but differentiator impact still needs product validation data. |
| Architecture | MEDIUM | Architecture is coherent and dependency-aware, but some scale details are inferred from patterns vs. benchmarked in this exact deployment. |
| Pitfalls | MEDIUM | Risks are credible and actionable, though several prevention thresholds need calibration with real traffic. |

**Overall confidence:** MEDIUM

### Gaps to Address

- **Enrichment provider selection and limits:** confirm concrete vendors, quotas, latency SLOs, and budget assumptions before Phase 3 execution.
- **Realtime scale envelope:** define explicit concurrent viewer and event-throughput targets to size fan-out architecture in Phase 4.
- **Analytics signal quality:** validate intent-scoring heuristics and false-positive tolerance before committing to advanced prioritization UX.
- **Operational observability baselines:** set measurable ingest/enrichment/websocket SLOs early so reliability claims are testable.

## Sources

### Primary (HIGH confidence)
- `/Users/rob/Documents/OT Apps/Holding Cell/.planning/research/STACK.md` — stack versions, compatibility, and recommended tooling
- `/Users/rob/Documents/OT Apps/Holding Cell/.planning/research/FEATURES.md` — MVP/differentiator/defer prioritization and dependencies
- `/Users/rob/Documents/OT Apps/Holding Cell/.planning/research/ARCHITECTURE.md` — component boundaries, data flow, and scaling pattern recommendations
- `/Users/rob/Documents/OT Apps/Holding Cell/.planning/research/PITFALLS.md` — phase-mapped risk model and prevention strategies
- `/Users/rob/Documents/OT Apps/Holding Cell/.planning/PROJECT.md` — project constraints, scope, and deployment context

### Secondary (MEDIUM confidence)
- https://docs.cowrie.org/en/latest/OUTPUT.html — Cowrie event model reference
- https://fastapi.tiangolo.com/advanced/websockets/ — FastAPI websocket implementation patterns
- https://www.postgresql.org/docs/current/datatype-json.html — JSONB behavior and trade-offs
- https://www.greynoise.io/products/threat-hunting — threat-intel product behavior benchmark
- https://github.com/telekom-security/tpotce — honeypot dashboard ecosystem reference

### Tertiary (LOW confidence)
- None identified in current research set.

---
*Research completed: 2026-03-03*
*Ready for roadmap: yes*
