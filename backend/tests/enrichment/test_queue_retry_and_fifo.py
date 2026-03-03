"""Queue execution tests for bounded retries, FIFO claiming, and status upgrades."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner
from app.services.enrichment_queue_service import enqueue_prisoner_enrichment, process_next_batch
from app.services.enrichment_service import EnrichmentResult


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
        enrichment_reason_metadata={
            "country_code": "pending",
            "asn": "pending",
            "reputation": "pending",
        },
        enrichment_provider=None,
        last_enriched_at=None,
    )


def _build_result(
    *,
    status: str,
    country_code: str | None,
    asn: str | None,
    reputation_severity: str | None,
    reputation_confidence: int | None,
    country_reason: str,
    asn_reason: str,
    reputation_reason: str,
    quota_limited: bool,
    enriched_at: datetime | None,
) -> EnrichmentResult:
    provider_parts: list[str] = []
    if country_code and asn:
        provider_parts.append("ipinfo")
    if reputation_severity and reputation_confidence is not None:
        provider_parts.append("abuseipdb")

    return EnrichmentResult(
        status=status,
        country_code=country_code,
        asn=asn,
        reputation_severity=reputation_severity,
        reputation_confidence=reputation_confidence,
        reason_metadata={
            "country_code": country_reason,
            "asn": asn_reason,
            "reputation": reputation_reason,
        },
        provider="+".join(provider_parts) if provider_parts else None,
        last_enriched_at=enriched_at,
        quota_limited=quota_limited,
    )


def test_process_next_batch_enforces_fifo_retry_bounds_and_upgrade_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'queue-worker.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    now = datetime.now(timezone.utc)

    with session_factory() as session:
        prisoner_a = _seed_prisoner(source_ip="203.0.113.40", observed_at=now - timedelta(minutes=3))
        prisoner_b = _seed_prisoner(source_ip="203.0.113.41", observed_at=now - timedelta(minutes=2))
        prisoner_c = _seed_prisoner(source_ip="203.0.113.42", observed_at=now - timedelta(minutes=1))
        session.add_all([prisoner_a, prisoner_b, prisoner_c])
        session.commit()

        enqueue_prisoner_enrichment(session=session, prisoner_id=prisoner_a.id, available_at=now - timedelta(seconds=30))
        enqueue_prisoner_enrichment(session=session, prisoner_id=prisoner_b.id, available_at=now - timedelta(seconds=20))
        enqueue_prisoner_enrichment(session=session, prisoner_id=prisoner_c.id, available_at=now - timedelta(seconds=10))

        job_c = session.execute(
            select(EnrichmentJob).where(EnrichmentJob.prisoner_id == prisoner_c.id)
        ).scalar_one()
        job_c.max_attempts = 1
        session.commit()

        responses = {
            prisoner_a.source_ip: [
                _build_result(
                    status="failed",
                    country_code=None,
                    asn=None,
                    reputation_severity=None,
                    reputation_confidence=None,
                    country_reason="quota_exceeded",
                    asn_reason="quota_exceeded",
                    reputation_reason="quota_exceeded",
                    quota_limited=True,
                    enriched_at=None,
                ),
                _build_result(
                    status="complete",
                    country_code="US",
                    asn="AS13335",
                    reputation_severity="high",
                    reputation_confidence=92,
                    country_reason="provider_success",
                    asn_reason="provider_success",
                    reputation_reason="provider_success",
                    quota_limited=False,
                    enriched_at=now + timedelta(minutes=5),
                ),
            ],
            prisoner_b.source_ip: [
                _build_result(
                    status="complete",
                    country_code="DE",
                    asn="AS3320",
                    reputation_severity="low",
                    reputation_confidence=10,
                    country_reason="provider_success",
                    asn_reason="provider_success",
                    reputation_reason="provider_success",
                    quota_limited=False,
                    enriched_at=now + timedelta(minutes=1),
                )
            ],
            prisoner_c.source_ip: [
                _build_result(
                    status="failed",
                    country_code=None,
                    asn=None,
                    reputation_severity=None,
                    reputation_confidence=None,
                    country_reason="provider_error",
                    asn_reason="provider_error",
                    reputation_reason="provider_error",
                    quota_limited=False,
                    enriched_at=None,
                )
            ],
        }
        call_order: list[str] = []

        def fake_enrich_ip_intel(*, source_ip: str, now: datetime | None = None, client=None) -> EnrichmentResult:
            call_order.append(source_ip)
            return responses[source_ip].pop(0)

        monkeypatch.setattr(
            "app.services.enrichment_queue_service.enrich_ip_intel",
            fake_enrich_ip_intel,
        )

        first = process_next_batch(session=session, batch_size=1, now=now)
        assert first == {
            "claimed_count": 1,
            "processed_count": 1,
            "completed_count": 0,
            "deferred_count": 1,
            "failed_count": 0,
        }

        second = process_next_batch(session=session, batch_size=2, now=now)
        assert second == {
            "claimed_count": 2,
            "processed_count": 2,
            "completed_count": 1,
            "deferred_count": 0,
            "failed_count": 1,
        }

        third = process_next_batch(session=session, batch_size=2, now=now + timedelta(seconds=130))
        assert third == {
            "claimed_count": 1,
            "processed_count": 1,
            "completed_count": 1,
            "deferred_count": 0,
            "failed_count": 0,
        }

        session.refresh(prisoner_a)
        session.refresh(prisoner_b)
        session.refresh(prisoner_c)

        assert call_order == [
            prisoner_a.source_ip,
            prisoner_b.source_ip,
            prisoner_c.source_ip,
            prisoner_a.source_ip,
        ]

        assert prisoner_a.enrichment_status == "complete"
        assert prisoner_a.enrichment_country_code == "US"
        assert prisoner_a.enrichment_asn == "AS13335"
        assert prisoner_a.enrichment_reputation_severity == "high"
        assert prisoner_a.enrichment_reputation_confidence == 92
        assert prisoner_a.last_enriched_at is not None

        assert prisoner_b.enrichment_status == "complete"
        assert prisoner_b.enrichment_provider == "ipinfo+abuseipdb"

        assert prisoner_c.enrichment_status == "failed"
        assert prisoner_c.enrichment_reason_metadata == {
            "country_code": "provider_error",
            "asn": "provider_error",
            "reputation": "provider_error",
        }

        failed_job_c = session.execute(
            select(EnrichmentJob).where(EnrichmentJob.prisoner_id == prisoner_c.id)
        ).scalar_one()
        assert failed_job_c.status == "failed"
