#!/usr/bin/env python3
"""One-shot queue drain command for deferred enrichment processing."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drain deferred enrichment jobs until queue is idle.")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--max-batches", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    session = None

    try:
        from app.db.session import create_session_factory
        from app.services.enrichment_queue_service import process_next_batch

        session_factory = create_session_factory()
        session = session_factory()

        claimed_count = 0
        processed_count = 0
        completed_count = 0
        deferred_count = 0
        failed_count = 0
        batches = 0

        while batches < max(args.max_batches, 1):
            batch_summary = process_next_batch(session=session, batch_size=max(args.batch_size, 1))
            if batch_summary["claimed_count"] == 0:
                break

            batches += 1
            claimed_count += batch_summary["claimed_count"]
            processed_count += batch_summary["processed_count"]
            completed_count += batch_summary["completed_count"]
            deferred_count += batch_summary["deferred_count"]
            failed_count += batch_summary["failed_count"]

        print(
            json.dumps(
                {
                    "status": "succeeded",
                    "finished_at": _utc_now_iso(),
                    "batches": batches,
                    "claimed_count": claimed_count,
                    "processed_count": processed_count,
                    "completed_count": completed_count,
                    "deferred_count": deferred_count,
                    "failed_count": failed_count,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:  # pragma: no cover - exercised in script-level failure tests.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "finished_at": _utc_now_iso(),
                    "error": str(exc),
                },
                sort_keys=True,
            )
        )
        return 1
    finally:
        if session is not None:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
