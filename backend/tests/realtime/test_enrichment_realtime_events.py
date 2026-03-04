"""Realtime publish tests for enrichment lifecycle mutations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.prisoner import Prisoner
from app.services.enrichment_queue_service import enqueue_prisoner_enrichment, process_next_batch
from app.services.enrichment_service import EnrichmentResult


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_process_next_batch_emits_prisoner_enriched_realtime_event_after_persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'enrichment-realtime.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    now = datetime(2026, 3, 4, 14, 0, tzinfo=timezone.utc)
    published: list[tuple[str, int]] = []

    monkeypatch.setattr("app.services.enrichment_queue_service.get_realtime_event_bus", lambda: object())

    def _capture_publish(*, session: Session, event_bus, event_name: str, prisoner_id: int) -> bool:
        published.append((event_name, prisoner_id))
        return True

    monkeypatch.setattr(
        "app.services.enrichment_queue_service.publish_prisoner_lifecycle_event",
        _capture_publish,
    )

    def _complete_enrichment(*, source_ip: str, now: datetime | None = None, client=None) -> EnrichmentResult:
        return EnrichmentResult(
            status="complete",
            country_code="US",
            asn="AS13335",
            reputation_severity="high",
            reputation_confidence=95,
            reason_metadata={
                "country_code": "provider_success",
                "asn": "provider_success",
                "reputation": "provider_success",
            },
            provider="ipinfo+abuseipdb",
            last_enriched_at=now,
            quota_limited=False,
        )

    monkeypatch.setattr(
        "app.services.enrichment_queue_service.enrich_ip_intel",
        _complete_enrichment,
    )

    with session_factory() as session:
        prisoner = Prisoner(
            source_ip="203.0.113.88",
            country_code=None,
            attempt_count=1,
            first_seen_at=now - timedelta(minutes=5),
            last_seen_at=now - timedelta(minutes=1),
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
        session.add(prisoner)
        session.commit()

        enqueue_prisoner_enrichment(
            session=session,
            prisoner_id=prisoner.id,
            available_at=now - timedelta(seconds=10),
        )

        result = process_next_batch(
            session=session,
            batch_size=1,
            now=now,
        )
        session.refresh(prisoner)

    assert result == {
        "claimed_count": 1,
        "processed_count": 1,
        "completed_count": 1,
        "deferred_count": 0,
        "failed_count": 0,
    }
    assert prisoner.enrichment_status == "complete"
    assert prisoner.enrichment_country_code == "US"
    assert prisoner.enrichment_asn == "AS13335"
    assert prisoner.enrichment_reputation_severity == "high"
    assert prisoner.enrichment_reputation_confidence == 95
    assert published == [("prisoner_enriched", prisoner.id)]
