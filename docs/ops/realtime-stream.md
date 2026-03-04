# Realtime Stream Operations Runbook

This runbook verifies websocket stream health for prisoner lifecycle and aggregate stats updates.

## Prerequisites

- Backend API URL (example: `https://api.holdingcell.example.com`)
- Allowed browser origin configured in `APPROVED_BROWSER_ORIGINS`
- A valid ingest API key for test mutations

## 1. Verify Websocket Sync Lifecycle

Connect to `wss://<api-host>/ws/events` from an approved origin and confirm this deterministic order:

1. `welcome`
2. `sync_start`
3. one or more `snapshot_chunk`
4. `stats_update`
5. `sync_complete`

If this order is broken, treat stream hydration as unhealthy.

## 2. Verify Live Mutation Continuity

With a websocket client still connected after `sync_complete`:

1. Send one ingest mutation to `POST /api/ingest` for a new `source_ip`.
2. Confirm a live `new_prisoner` event arrives on the existing websocket connection.
3. Send another ingest mutation for the same `source_ip`.
4. Confirm a live `prisoner_updated` event arrives.

If lifecycle events only appear after reconnect, investigate realtime publish wiring and event-bus subscriptions.

## 3. Verify Stats Cadence and Changed-Only Semantics

After initial `stats_update` in sync:

1. Hold system steady (no ingest/enrichment changes) for multiple cadence windows.
2. Confirm no repeated duplicate `stats_update` events are emitted.
3. Trigger one ingest mutation and confirm exactly one new `stats_update` with changed counters.

Expected: no per-mutation spam while idle, near-live updates when aggregate values actually change.

## 4. Verify Reconnect Recovery and Stale-State Handling

1. Disconnect websocket client.
2. Perform one ingest mutation while disconnected.
3. Reconnect to websocket endpoint.
4. Confirm sync lifecycle emits an authoritative snapshot containing the latest prisoner and stats state.

Operational expectation: reconnect always restores state before live fanout resumes.

## 5. Failure Signals and First Checks

- Missing `sync_complete`: check websocket origin policy and snapshot query path.
- Live prisoner events missing but ingest succeeds: verify mutation publishers and websocket fanout share the same realtime event bus.
- Duplicate/high-frequency `stats_update` while idle: inspect stats broadcaster change-detection state.
- No stats updates after real mutations: verify broadcaster lifecycle is running in app startup and not stopped unexpectedly.
