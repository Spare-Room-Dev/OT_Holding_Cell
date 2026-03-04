# The Holding Cell

## What This Is

The Holding Cell is a real-time threat-intelligence dashboard that turns Cowrie honeypot activity into an interactive analyst view with secure ingest, durable canonical attacker records, asynchronous enrichment, and live websocket updates.

## Core Value

Turn raw honeypot attack traffic into an immediate, understandable, real-time visual intelligence feed.

## Current State

- v1.0 MVP shipped on 2026-03-04.
- Delivered end-to-end ingest -> canonical persistence -> async enrichment -> realtime stream -> responsive dashboard loop.
- Milestone execution completed across 5 phases, 26 plans, and 52 tasks.
- Milestone audit verdict: `tech_debt` (no blocking gaps; one requirement partially externally verified).

## Next Milestone Goals

- Close `DATA-03` production proof with verified retention cron evidence.
- Add browser-level live backend wiring E2E coverage (reduce mocked-only risk).
- Resolve frontend endpoint/CSP topology coupling for split-domain deployments.
- Define and prioritize v1.1 requirements from deferred intelligence/integration/admin scope.

## Requirements

### Validated

- ✓ Trusted ingest boundary with API-key auth, source-IP allowlisting, validation hardening, idempotency, and rate limiting — v1.0
- ✓ Canonical prisoner persistence with deterministic pagination/detail APIs and retention hygiene — v1.0
- ✓ Async enrichment pipeline with durable queueing and graceful provider-failure handling — v1.0
- ✓ Reconnect-safe realtime prisoner/stat event streaming with read-only websocket posture — v1.0
- ✓ Responsive analyst dashboard with safe rendering, masked IP defaults, and operational filtering — v1.0

### Active

- [ ] Validate retention scheduler behavior in deployed environment and capture durable proof (`DATA-03` closure).
- [ ] Add live backend-wiring Playwright coverage alongside existing mocked dashboard E2E tests.
- [ ] Decouple runtime endpoint resolution and CSP topology assumptions.
- [ ] Convert deferred v2 requirements into an approved v1.1 milestone plan.

### Out of Scope

- Pixel-art walk-cycle prisoner sprites (deferred to post-core validation).
- OT/ICS control-room visual framing (deferred until post-v1.0 UX iteration).
- Public unmasked IP display (conflicts with public-safe posture).
- Full SOC case-management workflow (beyond current product boundary).

## Context

Current stack remains:
- Cowrie honeypot + forwarder on Vultr
- FastAPI + PostgreSQL backend on Render
- Vite + React + TypeScript frontend on Vercel

Milestone v1.0 delivery metrics:
- Git range: `feat(01-01)` -> `docs(v1.0)`
- Changes: 190 files, +21,240/-90 lines
- Timeline: 2026-03-03 -> 2026-03-04

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Vite React SPA (not SSR) | Product is realtime and interaction-first | ✓ Good |
| Persist in PostgreSQL on Render | Durable storage required for canonical attacker records | ✓ Good |
| Model prisoner detail history as JSON columns in v1 | Optimize for per-prisoner read patterns in MVP | ✓ Good |
| Keep frontend IP-masked by default | Maintain public-safe visibility posture | ✓ Good |
| Treat enrichment as async background work | Preserve ingest latency/availability during provider failures | ✓ Good |

---
*Last updated: 2026-03-04 after v1.0 milestone completion*
