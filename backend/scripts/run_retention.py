#!/usr/bin/env python3
"""Cron-safe retention command entrypoint."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.session import create_session_factory
from app.services.retention_service import run_retention_cycle


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    session_factory = create_session_factory()
    session = session_factory()
    try:
        summary = run_retention_cycle(session=session)
    except Exception as exc:  # pragma: no cover - exercised via scheduler error path.
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
        session.close()

    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
