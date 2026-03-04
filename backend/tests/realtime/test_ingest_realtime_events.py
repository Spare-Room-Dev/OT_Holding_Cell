"""Realtime event publishing tests for ingest lifecycle mutations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.prisoner import Prisoner
from app.realtime.publishers import publish_prisoner_lifecycle_event


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


class _CaptureBus:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def publish(self, event: str, payload: dict[str, object]) -> None:
        self.calls.append((event, payload))


def test_realtime_publish_helper_builds_full_summary_payload_with_stale_hint(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ingest-realtime-helper.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    now = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        prisoner = Prisoner(
            source_ip="203.0.113.66",
            country_code="US",
            attempt_count=5,
            first_seen_at=now,
            last_seen_at=now,
            credential_count=3,
            command_count=2,
            download_count=1,
            enrichment_status="complete",
            enrichment_country_code="US",
            enrichment_asn="AS13335",
            enrichment_reputation_severity="high",
            enrichment_reputation_confidence=90,
            enrichment_reason_metadata={
                "country_code": "provider_success",
                "asn": "provider_success",
                "reputation": "provider_success",
            },
            enrichment_provider="ipinfo+abuseipdb",
            last_enriched_at=now,
        )
        session.add(prisoner)
        session.commit()

        bus = _CaptureBus()
        emitted = publish_prisoner_lifecycle_event(
            session=session,
            event_bus=bus,
            event_name="new_prisoner",
            prisoner_id=prisoner.id,
        )

    assert emitted is True
    assert len(bus.calls) == 1

    event_name, payload = bus.calls[0]
    assert event_name == "new_prisoner"
    assert payload == {
        "prisoner_id": prisoner.id,
        "source_ip": "203.0.113.66",
        "country_code": "US",
        "attempt_count": 5,
        "first_seen_at": now,
        "last_seen_at": now,
        "credential_count": 3,
        "command_count": 2,
        "download_count": 1,
        "enrichment": {
            "status": "complete",
            "last_updated_at": now,
            "country_code": "US",
            "asn": "AS13335",
            "reputation_severity": "high",
        },
        "detail_sync_stale": True,
        "detail_last_changed_at": now,
    }


def test_realtime_publish_helper_ignores_missing_prisoner_ids(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'ingest-realtime-helper-missing.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    with session_factory() as session:
        bus = _CaptureBus()
        emitted = publish_prisoner_lifecycle_event(
            session=session,
            event_bus=bus,
            event_name="prisoner_updated",
            prisoner_id=404,
        )

    assert emitted is False
    assert bus.calls == []
