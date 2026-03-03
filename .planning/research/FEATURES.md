# Feature Research

**Domain:** gamified threat-intelligence honeypot dashboard
**Researched:** 2026-03-03
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Secure honeypot event ingest (auth, allowlist, validation, idempotency, rate limit) | Security users expect telemetry pipelines to be trustworthy and abuse-resistant | MEDIUM | Foundation for all downstream features; align with API-key + allowlist model in PROJECT.md |
| Live attack stream with auto-refresh timeline/cards | Threat dashboards are expected to surface activity in near real time, not as batch reports | MEDIUM | WebSocket/SSE event flow, reconnect strategy, and backpressure controls are required |
| Drill-down session detail (source IP, protocol, login attempts, commands, timestamps) | Cowrie-style honeypot value is in session-level behavior visibility | MEDIUM | Normalize Cowrie event types into a stable event schema before UI rendering |
| Basic enrichment and context (geo/IP reputation/threat tags) | Analysts expect immediate context to triage scanner noise vs notable activity | HIGH | Keep enrichment async to avoid blocking ingest; support partial-failure states |
| Filtering/search and top-level stats (top sources, protocols, attempt counts) | SOC users expect fast pivoting and quick summaries before deep investigation | MEDIUM | Filter by time window, protocol, enrichment status, and repeat-offender counts |
| Safe public presentation (masked IPs, sanitized attacker strings, read-only client) | Public-facing security demos are expected to avoid exposing sensitive details or executing attacker content | LOW | Mandatory output encoding + IP masking policy in frontend |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Retro prison-cell simulation where attackers appear as moving "prisoners" | Makes threat telemetry immediately understandable and memorable for non-SOC stakeholders | MEDIUM | Keep simulation coupled to real events (spawn/update/enrich) rather than cosmetic loops |
| Narrative threat cards ("what happened" + "why it matters") | Converts raw events into portfolio-friendly intelligence storytelling | MEDIUM | Rule-based summarization first; optional LLM summarization later |
| Intent scoring lane (opportunistic scanner vs suspicious behavior) | Prioritizes analyst attention and reduces noise fatigue | HIGH | Derive from repeated attempts, command patterns, threat tags, and velocity heuristics |
| Replay mode for notable attack sessions | Demonstrates behavior over time and improves incident review/training value | HIGH | Build from persisted event stream with deterministic playback controls |
| "Campaign pulse" clustering (group similar sources/behaviors) | Surfaces broader patterns instead of isolated IP events | HIGH | Start with simple heuristic clustering before full graph analytics |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Unmasked attacker IPs and raw IOC export in public UI | Feels "more authentic" and useful for immediate IOC sharing | Increases legal/privacy risk, encourages unsafe handling, and conflicts with public-demo posture | Mask by default; keep full-IP access behind private admin/audited API in later phase |
| Multi-honeypot/multi-sensor ingestion in v1 | Sounds like faster coverage and bigger data volume | Multiplies integration and normalization complexity before core loop is reliable | Ship single Cowrie sensor path first, then add adapter interface for v1.x |
| Real-time everything (all animations + all raw events rendered) | Looks impressive in demos | Causes UI overload, performance regressions, and operator fatigue | Curate event priority lanes, throttle low-value updates, and summarize bursts |
| Full SOC case management in-product | Mimics mature SOC platforms | Large workflow surface area with low value for initial validation | Provide outbound webhooks/export hooks into existing SOC tools |

## Feature Dependencies

```
[Secure Ingest]
    └──requires──> [Event Normalization + Validation]
                       └──requires──> [Persistent Attacker Store]
                                          └──requires──> [WebSocket Event Broadcast]
                                                             └──requires──> [Live Dashboard UI]

[Async Enrichment] ──enhances──> [Session Detail + Intent Scoring]

[Replay Mode] ──requires──> [Persisted Ordered Event History]

[Public Unmasked IP Access] ──conflicts──> [Safe Public Presentation]

[Multi-Sensor Ingestion] ──conflicts──> [Fast v1 Validation Scope]
```

### Dependency Notes

- **Secure Ingest requires Event Normalization + Validation:** without a canonical event contract, downstream storage, enrichment, and UI behavior become brittle and inconsistent.
- **Persistent Attacker Store requires normalized events:** aggregation, deduplication, and repeat-attempt counting depend on stable keys and timestamps.
- **WebSocket Event Broadcast requires persisted state:** reconnect/replay and correctness under transient client disconnects depend on source-of-truth storage.
- **Async Enrichment enhances Session Detail + Intent Scoring:** enrichment adds context and better prioritization, but should not block first render of new events.
- **Replay Mode requires persisted ordered event history:** deterministic playback cannot be built from transient live events alone.
- **Public Unmasked IP Access conflicts with Safe Public Presentation:** threat-data transparency goals clash with portfolio-safe privacy posture.
- **Multi-Sensor Ingestion conflicts with Fast v1 Validation Scope:** broad ingestion is valuable later but dilutes effort from proving the core live loop.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] Secure single-sensor Cowrie ingest pipeline — proves trustworthy data capture and reliability
- [ ] Live dashboard with prisoner visualization + detail pane + stats bar — validates core engagement loop
- [ ] Async enrichment with graceful partial-failure handling — delivers usable threat context without ingest slowdown
- [ ] Filtering/time window controls + repeat-attempt aggregation — makes the dashboard operationally useful
- [ ] Safe public rendering defaults (masked IPs, sanitized output, read-only client) — protects security posture for public use

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Intent scoring lane and anomaly highlighting — add once baseline event quality and false-positive rates are understood
- [ ] Replay mode for notable sessions — add once stable event retention and UI interaction metrics justify it
- [ ] Alert/webhook integrations (Slack/Discord/SIEM) — add once users request operational handoff from dashboard insights

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Multi-honeypot ingestion adapters (beyond Cowrie) — defer until single-sensor workflow is proven and maintainable
- [ ] Private analyst/admin workspace with unmasked IOCs and RBAC — defer until clear enterprise demand exists
- [ ] Campaign-level clustering and graph analytics — defer until sufficient data scale supports meaningful correlation

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Secure ingest + normalization | HIGH | MEDIUM | P1 |
| Live event dashboard (cell + detail + stats) | HIGH | MEDIUM | P1 |
| Async enrichment pipeline | HIGH | HIGH | P1 |
| Filtering/search/time windows | HIGH | MEDIUM | P1 |
| Masked/sanitized public UI | HIGH | LOW | P1 |
| Intent scoring lane | MEDIUM | HIGH | P2 |
| Replay mode | MEDIUM | HIGH | P2 |
| Alert/webhook integrations | MEDIUM | MEDIUM | P2 |
| Multi-sensor ingestion | MEDIUM | HIGH | P3 |
| Analyst admin workspace | MEDIUM | HIGH | P3 |
| Campaign clustering analytics | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A | Competitor B | Our Approach |
|---------|--------------|--------------|--------------|
| Honeypot telemetry visualization | T-Pot offers Kibana dashboards and an attack map for honeypot data | GreyNoise Visualizer emphasizes internet-wide scanner intelligence views | Blend operational live feed with gamified but data-true visualization |
| Real-time event handling | T-Pot attack map/dashboard updates from honeypot streams | GreyNoise Feeds provides near-real-time attacker activity updates | WebSocket events with explicit `new/update/enriched/stats` lifecycle |
| Analyst triage context | T-Pot relies on Elastic/Kibana exploration | GreyNoise focuses on filtering benign internet noise and surfacing meaningful signals | Add lightweight intent scoring + narrative context for faster comprehension |
| Alerting/integration posture | T-Pot is powerful but infrastructure-heavy for small teams | Shodan Monitor exposes notifications and API-driven automation | Keep core dashboard focused; add webhooks after v1 validation |
| Safety/public sharing | Many SOC tools assume private internal usage | Commercial platforms are account-gated | Design public-safe defaults first (masking/sanitization/read-only) |

## Sources

- PROJECT context: `/Users/rob/Documents/OT Apps/Holding Cell/.planning/PROJECT.md`
- Cowrie output/event model: https://docs.cowrie.org/en/latest/OUTPUT.html
- Cowrie repository capabilities: https://github.com/cowrie/cowrie
- T-Pot CE platform (Kibana dashboards + attack map): https://github.com/telekom-security/tpotce
- Security Onion dashboards/alerts behavior: https://docs.securityonion.net/en/2.4/dashboards and https://docs.securityonion.net/en/2.4/alerts.html
- GreyNoise Visualizer/Threat Hunting and Feeds: https://www.greynoise.io/products/threat-hunting and https://docs.greynoise.io/docs/event-feeds
- Shodan Monitor capabilities/notifications/API feed: https://monitor.shodan.io/ and https://help.shodan.io/shodan-monitor/consume-data-feed

---
*Feature research for: gamified threat-intelligence honeypot dashboard*
*Researched: 2026-03-03*
