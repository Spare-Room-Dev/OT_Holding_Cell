# Retention Cron Runbook

## Purpose
Run daily retention to purge stale detail rows while preserving lifetime headline rollups.

## Render Cron Job Setup
1. Open Render dashboard for the backend service.
2. Go to `Cron Jobs`.
3. Create a daily job with command:

```bash
cd /opt/render/project/src/backend && python scripts/run_retention.py
```

4. Ensure `DATABASE_URL` is set on the backend service environment.

## Expected Script Contract
- Exit code `0` on success.
- Exit code non-zero on failure.
- Standard output emits one JSON object with at least:
  - `status`
  - `run_id`
  - `deleted_prisoner_count`
  - `deleted_delivery_count`
  - `prisoner_cutoff_at`
  - `delivery_cutoff_at`

Example success output:

```json
{
  "deleted_delivery_count": 4,
  "deleted_prisoner_count": 2,
  "delivery_cutoff_at": "2026-03-03T12:00:00+00:00",
  "finished_at": "2026-03-03T12:00:00+00:00",
  "prisoner_cutoff_at": "2026-02-01T12:00:00+00:00",
  "run_id": 13,
  "started_at": "2026-03-03T12:00:00+00:00",
  "status": "succeeded"
}
```

## Verification Checklist
1. Confirm latest cron execution succeeded in Render dashboard.
2. Validate JSON summary reports non-negative delete counts.
3. If counts spike unexpectedly, inspect recent ingest volume and retention cutoffs before taking action.
