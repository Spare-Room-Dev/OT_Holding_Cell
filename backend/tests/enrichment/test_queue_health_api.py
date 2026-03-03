"""API contract tests for enrichment queue health visibility."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import app.db.session as db_session_module
from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner


def _create_prisoner(*, source_ip: str, timestamp: datetime) -> int:
    with db_session_module.SessionFactory() as session:
        prisoner = Prisoner(
            source_ip=source_ip,
            country_code="US",
            attempt_count=1,
            first_seen_at=timestamp,
            last_seen_at=timestamp,
            credential_count=0,
            command_count=0,
            download_count=0,
        )
        session.add(prisoner)
        session.flush()
        session.commit()
        return prisoner.id


def _add_queue_job(
    *,
    prisoner_id: int,
    status: str,
    created_at: datetime,
    available_at: datetime,
) -> None:
    with db_session_module.SessionFactory() as session:
        session.add(
            EnrichmentJob(
                prisoner_id=prisoner_id,
                status=status,
                attempt_count=0,
                max_attempts=3,
                available_at=available_at,
                created_at=created_at,
                failure_reason_metadata={},
            )
        )
        session.commit()


def test_enrichment_queue_health_reports_counts_and_oldest_pending_age(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    prisoner_id = _create_prisoner(source_ip="203.0.113.200", timestamp=now - timedelta(hours=1))

    _add_queue_job(
        prisoner_id=prisoner_id,
        status="queued",
        created_at=now - timedelta(seconds=180),
        available_at=now - timedelta(seconds=180),
    )
    _add_queue_job(
        prisoner_id=prisoner_id,
        status="in_progress",
        created_at=now - timedelta(seconds=60),
        available_at=now - timedelta(seconds=60),
    )
    _add_queue_job(
        prisoner_id=prisoner_id,
        status="failed",
        created_at=now - timedelta(seconds=240),
        available_at=now - timedelta(seconds=240),
    )
    _add_queue_job(
        prisoner_id=prisoner_id,
        status="completed",
        created_at=now - timedelta(seconds=300),
        available_at=now - timedelta(seconds=300),
    )

    response = client.get("/api/ops/enrichment-queue")
    assert response.status_code == 200
    payload = response.json()

    assert payload["queued_count"] == 1
    assert payload["pending_count"] == 2
    assert payload["failed_count"] == 1
    assert isinstance(payload["oldest_pending_age_seconds"], int)
    assert payload["oldest_pending_age_seconds"] >= 180


def test_enrichment_queue_health_returns_zeroes_when_no_jobs_exist(client: TestClient) -> None:
    response = client.get("/api/ops/enrichment-queue")
    assert response.status_code == 200
    assert response.json() == {
        "queued_count": 0,
        "pending_count": 0,
        "failed_count": 0,
        "oldest_pending_age_seconds": None,
    }
