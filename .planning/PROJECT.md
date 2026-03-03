# The Holding Cell

## What This Is

The Holding Cell is a gamified threat-intelligence dashboard that visualizes real Cowrie honeypot attacks as moving "prisoners" in a retro jail-cell interface. It ingests live SSH/Telnet attack activity from a hardened forwarder, enriches it with threat intel, and streams updates to a React frontend in near real time. The primary audience is security practitioners and portfolio reviewers who want a clear, engaging view of hostile traffic patterns.

## Core Value

Turn raw honeypot attack traffic into an immediate, understandable, real-time visual intelligence feed.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Securely ingest and validate Cowrie attack sessions from a VPS forwarder with API-key auth, IP allowlisting, idempotency, and rate limiting.
- [ ] Persist unique attacker records in PostgreSQL with repeat-attempt aggregation, enrichment status, and retention cleanup.
- [ ] Enrich new attacker IPs with geo/threat-intel signals and handle partial failures without blocking ingest.
- [ ] Stream `new_prisoner`, `prisoner_updated`, `prisoner_enriched`, and `stats_update` events to the frontend over WebSocket.
- [ ] Render a responsive "cell + detail pane + stats bar" UI where users can inspect attacker behavior and threat context.

### Out of Scope

- Pixel-art walk-cycle avatars in v1 — deferred to keep v1 focused on reliability and core data flow.
- OT/ICS control-room theming and advanced visual polish in v1 — deferred until core interaction loop is stable.
- Multi-honeypot ingestion in v1 — single-sensor path first to reduce operational complexity.
- Admin panel with unmasked IP access in v1 — public dashboard remains masked by default.
- PDF export and historical timeline features in v1 — defer until primary live-view workflow proves value.

## Context

System shape is explicitly three-tier:
- Cowrie honeypot on Vultr + Python forwarder (outbound HTTPS only)
- FastAPI backend on Render with async PostgreSQL persistence and WebSocket broadcasting
- Vite + React + TypeScript frontend on Vercel

Security posture is a first-class requirement:
- Authenticated ingest (`Bearer` API key), forwarder IP allowlisting, strict payload validation, and endpoint rate limiting
- Client is read-only over WebSocket (no custom inbound client events processed)
- Sensitive values stay server-side; frontend renders masked IPs and sanitized attacker-controlled strings

Operational behavior is event-driven and resilient:
- New IPs are inserted quickly, enrichment runs asynchronously, partial API failures degrade gracefully
- Forwarder includes retry + dead-letter + heartbeat semantics
- Data retention and idempotency controls prevent duplication and unbounded growth

## Constraints

- **Hosting**: Use Vultr (honeypot), Render (backend + Postgres), and Vercel (frontend) — architecture is already selected in design.
- **Security**: No secrets in frontend bundles, strict CORS/CSP, allowlisted forwarder ingress only — required by threat model.
- **Performance**: Target smooth animation and interaction with up to 25 visible prisoners (desktop baseline) — avoids UI degradation.
- **Scope**: v1 prioritizes live ingest → enrichment → visualization loop over advanced theming/features — ensures shippable core.
- **Data Retention**: Purge prisoner records older than 30 days and idempotency records older than 7 days — limits storage growth.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Vite React SPA (not SSR) | Product is real-time, interaction-first, and non-SEO | — Pending |
| Persist in PostgreSQL (not SQLite) on Render | Free-tier filesystem is ephemeral; DB durability is required | — Pending |
| Model prisoner details with JSON columns in v1 | Read patterns are per-prisoner detail, reducing JOIN complexity initially | — Pending |
| Keep frontend IP-masked by default | Public portfolio display should minimize exposure risk | — Pending |
| Treat enrichment as async background work | Ingest latency and availability should not depend on third-party APIs | — Pending |

---
*Last updated: 2026-03-03 after initialization*
