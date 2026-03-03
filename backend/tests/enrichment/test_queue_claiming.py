"""Deferred enrichment queue lifecycle tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner
from app.services.enrichment_queue_service import (
    claim_enrichment_jobs,
    defer_enrichment_job,
    enqueue_prisoner_enrichment,
)


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _seed_prisoner(*, source_ip: str, observed_at: datetime) -> Prisoner:
    return Prisoner(
        source_ip=source_ip,
        country_code=None,
        attempt_count=1,
        first_seen_at=observed_at,
        last_seen_at=observed_at,
        credential_count=0,
        command_count=0,
        download_count=0,
        enrichment_status="pending",
        enrichment_country_code=None,
        enrichment_asn=None,
        enrichment_reputation_severity=None,
        enrichment_reputation_confidence=None,
        enrichment_reason_metadata={"country_code": "pending", "asn": "pending", "reputation": "pending"},
        enrichment_provider=None,
        last_enriched_at=None,
    )


def _coerce_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def test_queue_claiming_respects_fifo_and_retry_deferral_rules(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue-claiming.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    now = datetime.now(timezone.utc)

    with SessionFactory() as session:
        prisoners = [
            _seed_prisoner(source_ip="203.0.113.20", observed_at=now - timedelta(minutes=3)),
            _seed_prisoner(source_ip="203.0.113.21", observed_at=now - timedelta(minutes=2)),
            _seed_prisoner(source_ip="203.0.113.22", observed_at=now - timedelta(minutes=1)),
        ]
        session.add_all(prisoners)
        session.commit()

        enqueue_prisoner_enrichment(session=session, prisoner_id=prisoners[0].id, available_at=now - timedelta(seconds=30))
        enqueue_prisoner_enrichment(session=session, prisoner_id=prisoners[1].id, available_at=now - timedelta(seconds=10))
        enqueue_prisoner_enrichment(session=session, prisoner_id=prisoners[2].id, available_at=now + timedelta(seconds=60))

        claimed = claim_enrichment_jobs(session=session, batch_size=5, now=now)
        assert [job.prisoner_id for job in claimed] == [prisoners[0].id, prisoners[1].id]
        assert all(job.status == "in_progress" for job in claimed)
        assert all(job.claimed_at is not None for job in claimed)

        deferred = defer_enrichment_job(
            session=session,
            job_id=claimed[0].id,
            reason_metadata={"provider_error": "quota_exceeded"},
            now=now,
            quota_limited=True,
        )
        assert deferred is not None
        assert deferred.status == "queued"
        assert deferred.attempt_count == 1
        assert _coerce_utc(deferred.available_at) >= now + timedelta(seconds=120)
        assert deferred.failure_reason_metadata["provider_error"] == "quota_exceeded"

        to_fail = session.get(EnrichmentJob, claimed[1].id)
        assert to_fail is not None
        to_fail.max_attempts = 1
        session.commit()

        exhausted = defer_enrichment_job(
            session=session,
            job_id=claimed[1].id,
            reason_metadata={"provider_error": "quota_exceeded"},
            now=now,
            quota_limited=False,
        )
        assert exhausted is not None
        assert exhausted.status == "failed"
        assert exhausted.attempt_count == 1
        assert exhausted.completed_at is not None
        assert exhausted.failure_reason_metadata["provider_error"] == "quota_exceeded"
