# Stack Research

**Domain:** Gamified threat-intelligence honeypot dashboard (real-time ingest + enrichment + live visualization)
**Researched:** 2026-03-03
**Confidence:** MEDIUM

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.13.x | Backend runtime for ingest, enrichment, and streaming | Strong async ecosystem, mature security tooling, and excellent fit for FastAPI + threat-intel integrations. |
| FastAPI | 0.135.1 | API ingest layer + WebSocket event broadcasting | High-performance ASGI framework with typed validation and low overhead for real-time APIs. |
| PostgreSQL | 18.x (target 18.3) | Durable attacker/event storage, aggregation, retention | Reliable relational core with JSONB and indexing flexibility for evolving threat-intel schemas. |
| React | 19.2.4 | Interactive prison-cell dashboard UI | Mature ecosystem and excellent rendering model for high-frequency UI updates. |
| Vite | 7.3.1 | Frontend build tooling and fast DX | Fast local iteration and production builds; first-class React support and modern ESM workflow. |
| TypeScript | 5.9.3 | Type-safe frontend and shared contracts | Reduces runtime bugs in event-driven UIs and makes schema drift visible during development. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.12.5 | Strict payload validation and response modeling | Use on every ingest/event contract boundary to reject malformed attacker-controlled input. |
| SQLAlchemy | 2.0.48 | Async ORM and query layer | Use for domain models, transactional writes, and composable query logic over prisoner/session data. |
| alembic | 1.18.4 | Schema migration management | Use for all DB schema changes; never apply manual production DDL outside migrations. |
| psycopg | 3.3.3 | PostgreSQL driver (sync + async support) | Use as default DB driver for FastAPI services on Render; prefer one driver stack to reduce ops complexity. |
| uvicorn | 0.41.0 | ASGI server for FastAPI | Use for API/websocket serving in production containers behind Render edge proxy. |
| @tanstack/react-query | 5.90.21 | Server-state caching and synchronization | Use for non-streaming reads (bootstrap/state refresh), while WebSocket handles live deltas. |
| zustand | 5.0.11 | Lightweight client-side state for animation/UI controls | Use for ephemeral UI state (selected prisoner, filters, animation toggles), not backend truth. |
| zod | 4.3.6 | Runtime validation on frontend event payloads | Use to guard websocket payload parsing before updating visual state. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python env + dependency management | Prefer `uv lock` and committed lockfile for reproducible backend builds. |
| pytest | Backend test framework | Add API contract, idempotency, and enrichment failure-path tests early. |
| Vitest | Frontend unit/component testing | Pair with React Testing Library for event/render logic checks. |
| Playwright | End-to-end dashboard flow verification | Use for websocket-driven UI smoke tests before deployment. |
| Docker Compose | Local multi-service integration (API + DB + forwarder) | Use a single compose file to validate ingest-to-UI flow before cloud deployment. |

## Installation

```bash
# Core (backend)
uv add "fastapi==0.135.1" "uvicorn==0.41.0" "pydantic==2.12.5" "sqlalchemy==2.0.48" "psycopg==3.3.3" "alembic==1.18.4"

# Supporting (frontend)
npm install react@19.2.4 react-dom@19.2.4 @tanstack/react-query@5.90.21 zustand@5.0.11 zod@4.3.6

# Dev dependencies
npm install -D vite@7.3.1 @vitejs/plugin-react@5.1.4 typescript@5.9.3 vitest@4.0.18 playwright
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Django + DRF | Choose Django when built-in admin, ORM-heavy CRUD, and complex back-office workflows dominate over low-latency streaming. |
| PostgreSQL 18 | ClickHouse | Choose ClickHouse when ingest volume reaches analytics-scale OLAP needs (billions of events, heavy time-series scans). |
| React + Vite SPA | Next.js App Router | Choose Next.js when SSR/SEO or edge-rendered content is a major product requirement. |
| Native WebSocket event stream | Socket.IO | Choose Socket.IO only if you explicitly need legacy transport fallbacks and richer bidirectional semantics. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SQLite for production ingest storage | Insufficient concurrency and durability profile for continuously streaming honeypot events on hosted platforms. | PostgreSQL 18 on Render managed Postgres. |
| Create React App for new builds | Deprecated trajectory and slower toolchain for modern React apps. | React 19 + Vite 7. |
| Blocking enrichment in the ingest request path | Third-party intel API delays/failures will degrade ingest reliability and increase drop risk. | Async enrichment worker flow with immediate ingest ACK. |
| Storing unvalidated attacker payloads directly in UI state | Increases XSS/data-corruption risk from hostile input. | Strict schema validation (Pydantic + Zod) and sanitized rendering. |

## Stack Patterns by Variant

**If v1 single-sensor portfolio deployment (current plan):**
- Use one FastAPI service + one Postgres instance + async enrichment job path.
- Because it minimizes operational overhead while preserving the complete ingest-enrich-visualize loop.

**If scaling to multi-honeypot/high-throughput telemetry:**
- Use Redis/Kafka buffer between ingest and enrichment, plus read-optimized analytics store as needed.
- Because burst absorption and decoupled consumers prevent websocket/UI lag under attack spikes.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| fastapi@0.135.1 | pydantic@2.12.5 | FastAPI now runs on the Pydantic v2 model stack; keep these aligned. |
| sqlalchemy@2.0.48 | psycopg@3.3.3 | Stable modern Postgres integration for Python services. |
| vite@7.3.1 | node@22.12+ / 24.x | Vite 7 requires modern Node; use active LTS (24.x) when available. |
| react@19.2.4 | @vitejs/plugin-react@5.1.4 | Plugin line supports React 19 workflows in Vite 7 projects. |
| typescript@5.9.3 | react@19.2.4 | Strong typing support for React 19 app code and toolchain. |

## Sources

- https://pypi.org/pypi/fastapi/json — verified latest FastAPI version (HIGH)
- https://pypi.org/pypi/pydantic/json — verified latest Pydantic version (HIGH)
- https://pypi.org/pypi/sqlalchemy/json — verified latest SQLAlchemy version (HIGH)
- https://pypi.org/pypi/uvicorn/json — verified latest Uvicorn version (HIGH)
- https://pypi.org/pypi/alembic/json — verified latest Alembic version (HIGH)
- https://pypi.org/pypi/psycopg/json — verified latest Psycopg version (HIGH)
- https://registry.npmjs.org/react — verified React dist-tags/latest (HIGH)
- https://registry.npmjs.org/vite — verified Vite dist-tags/latest (HIGH)
- https://registry.npmjs.org/typescript — verified TypeScript dist-tags/latest (HIGH)
- https://registry.npmjs.org/@tanstack/react-query — verified TanStack Query dist-tags/latest (HIGH)
- https://vite.dev/guide/ — verified Vite Node version requirements (HIGH)
- https://www.postgresql.org/versions.json — verified supported/current PostgreSQL major versions (HIGH)
- https://render.com/docs/postgresql-upgrading — verified Render-supported PostgreSQL majors (HIGH)

---
*Stack research for: Gamified threat-intelligence honeypot dashboard*
*Researched: 2026-03-03*
