# Dashboard UI Verification Runbook

## Purpose
Validate that the analyst dashboard remains responsive, operationally usable, and safe after deploys or frontend changes.

## Scope
- Responsive layout behavior (desktop and mobile fallback)
- Connection health, stale-state visibility, and manual retry flow
- Country/time-window filter behavior and filtered-out counters
- Severity visual updates after enrichment-style events
- Safe rendering and masked-IP defaults for attacker-controlled data

## Prerequisites
- Frontend dependencies installed in `frontend/`
- Backend reachable at the same origin used by the frontend
- Browser access to the dashboard UI

## Automated Baseline
Run the tagged browser suite before manual checks:

```bash
cd frontend && npm run test:e2e -- --project=chromium --grep @dashboard
```

Expected result: all `@dashboard` tests pass.

## Manual Verification Checklist

### 1) Responsive Layout
1. Open the dashboard on desktop width (>= 1280px).
2. Confirm header, stats, filter controls, prisoner list, and detail region are visible together.
3. Switch to mobile width (around 390px).
4. Confirm list remains primary, detail uses a drawer, and drawer can be closed.

### 2) Connection Health, Stale State, and Retry
1. Confirm header pill initially shows `Connection live`.
2. Simulate a temporary disconnect (network toggle, backend pause, or websocket interruption).
3. Confirm UI moves to reconnecting/offline indicators and marks data as stale.
4. Click `Retry` and confirm reconnect attempt metadata updates.
5. After recovery, confirm connection returns to live and stale indicators clear.

### 3) Filter Validation
1. Set a country filter and confirm visible row count changes.
2. Set a tighter time window (for example `Last 15 minutes`) and confirm filtered results update immediately.
3. While filters are active, generate or replay a non-matching event and confirm filtered-out counters increase.

### 4) Severity Update Validation
1. Note current severity label and signal for a visible prisoner.
2. Trigger or replay an enrichment-style update that should change severity.
3. Confirm severity text/signal updates and the row visually reflects the change.

### 5) Safe Rendering and Masked-IP Defaults
1. Confirm both list-level and detail-pane source IP values are masked by default (for example `198.51.x.x`).
2. Verify attacker-controlled text values render as plain text (no executed markup/scripts).
3. Confirm the selected-prisoner detail pane never shows a full raw source IP value.
4. Confirm no unsafe HTML rendering appears in prisoner list or detail sections.

## Failure Signals
- Layout overlap, clipped content, or unusable mobile drawer.
- Connection stuck in reconnecting/offline without retry recovery.
- Filters not updating counts, or counters inconsistent with visible rows.
- Severity changes not reflected after enrichment updates.
- Unmasked source IP shown by default where masking is expected.
- Any unsafe attacker string rendering behavior.
