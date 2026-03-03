#!/usr/bin/env python3
"""Continuous worker loop for deferred enrichment queue processing."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import time


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continuously process deferred enrichment queue jobs.")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--poll-interval-seconds", type=float, default=5.0)
    parser.add_argument("--max-loops", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    session = None

    loops = 0
    claimed_count = 0
    processed_count = 0
    completed_count = 0
    deferred_count = 0
    failed_count = 0

    try:
        from app.db.session import create_session_factory
        from app.services.enrichment_queue_service import process_next_batch

        session_factory = create_session_factory()
        session = session_factory()

        while True:
            loops += 1
            batch_summary = process_next_batch(session=session, batch_size=max(args.batch_size, 1))
            claimed_count += batch_summary["claimed_count"]
            processed_count += batch_summary["processed_count"]
            completed_count += batch_summary["completed_count"]
            deferred_count += batch_summary["deferred_count"]
            failed_count += batch_summary["failed_count"]

            if args.max_loops is not None and loops >= max(args.max_loops, 1):
                break

            if batch_summary["claimed_count"] == 0:
                time.sleep(max(args.poll_interval_seconds, 0.0))

        print(
            json.dumps(
                {
                    "status": "succeeded",
                    "finished_at": _utc_now_iso(),
                    "loops": loops,
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
    except KeyboardInterrupt:  # pragma: no cover - operational path.
        print(
            json.dumps(
                {
                    "status": "stopped",
                    "finished_at": _utc_now_iso(),
                    "loops": loops,
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
