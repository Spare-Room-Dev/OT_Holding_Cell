# Enrichment Queue Health Runbook

## Purpose
Expose queue pressure and aging signals so operators can verify deferred enrichment is keeping up.

## Endpoint
- Method: `GET`
- Path: `/api/ops/enrichment-queue`
- Success status: `200`

Example response:

```json
{
  "queued_count": 3,
  "pending_count": 4,
  "failed_count": 1,
  "oldest_pending_age_seconds": 287
}
```

When there are no queued or in-progress jobs:

```json
{
  "queued_count": 0,
  "pending_count": 0,
  "failed_count": 0,
  "oldest_pending_age_seconds": null
}
```

## Signal Definitions
- `queued_count`: jobs waiting to be claimed.
- `pending_count`: jobs still in flight (`queued` + `in_progress`).
- `failed_count`: jobs in terminal failure state.
- `oldest_pending_age_seconds`: age of the oldest pending job in seconds, or `null` when nothing is pending.

## Verification Checklist
1. Call `GET /api/ops/enrichment-queue`.
2. Confirm response shape matches the contract above.
3. With an idle queue, verify all counts are `0` and `oldest_pending_age_seconds` is `null`.
4. During ingest bursts, watch `pending_count` and `oldest_pending_age_seconds`; both should fall back down after worker catch-up.
5. If `failed_count` rises or oldest pending age keeps increasing, investigate worker failures and retry settings.
