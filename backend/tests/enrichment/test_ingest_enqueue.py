"""Ingest-to-enrichment queue handoff tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.enrichment_job import EnrichmentJob
from app.models.prisoner import Prisoner


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _trusted_headers(source_ip: str = "203.0.113.10") -> dict[str, str]:
    return {
        "Authorization": "Bearer current-forwarder-key",
        "X-Forwarded-For": source_ip,
    }


def _valid_ingest_payload(*, delivery_id: str | None = None) -> dict[str, object]:
    return {
        "delivery_id": delivery_id or str(uuid4()),
        "protocol": "ssh",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "credentials": ["root:toor"],
        "commands": ["whoami"],
        "downloads": ["http://example.invalid/malware.bin"],
    }


@pytest.fixture
def ingest_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str]:
    database_path = tmp_path / "ingest-enqueue.sqlite3"
    database_url = f"sqlite:///{database_path}"
    command.upgrade(_alembic_config(database_url), "head")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", "current-forwarder-key")
    monkeypatch.setenv("INGEST_API_KEY_PREVIOUS", "previous-forwarder-key")
    monkeypatch.setenv("ALLOWED_FORWARDER_IPS", "[\"203.0.113.10\", \"203.0.113.11\", \"127.0.0.1\"]")

    from app.core.config import get_settings
    from app.db.session import create_session_factory
    from app.main import create_app
    import app.db.session as db_session_module

    get_settings.cache_clear()
    db_session_module.SessionFactory = create_session_factory(database_url)
    return TestClient(create_app()), database_url


def test_new_prisoner_ingest_enqueues_pending_enrichment_without_blocking_response(
    ingest_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, database_url = ingest_client
    first_payload = _valid_ingest_payload()

    first_response = client.post("/api/ingest", headers=_trusted_headers(), json=first_payload)
    duplicate_response = client.post("/api/ingest", headers=_trusted_headers(), json=first_payload)

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "processed"
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["status"] == "duplicate_ignored"

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        prisoner = session.query(Prisoner).filter(Prisoner.source_ip == "203.0.113.10").one()
        active_jobs = (
            session.query(EnrichmentJob)
            .filter(
                EnrichmentJob.prisoner_id == prisoner.id,
                EnrichmentJob.status.in_(("queued", "in_progress")),
            )
            .all()
        )

        assert prisoner.enrichment_status == "pending"
        assert prisoner.enrichment_country_code is None
        assert prisoner.enrichment_asn is None
        assert prisoner.enrichment_reputation_severity is None
        assert prisoner.enrichment_reputation_confidence is None
        assert prisoner.last_enriched_at is None
        assert prisoner.enrichment_reason_metadata == {
            "country_code": "pending",
            "asn": "pending",
            "reputation": "pending",
        }
        assert len(active_jobs) == 1
        assert active_jobs[0].status == "queued"
        assert active_jobs[0].attempt_count == 0

    monkeypatch.setattr(
        "app.services.ingest_service.enqueue_prisoner_enrichment",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("queue unavailable")),
    )

    second_response = client.post(
        "/api/ingest",
        headers=_trusted_headers("203.0.113.11"),
        json=_valid_ingest_payload(),
    )
    assert second_response.status_code == 200
    assert second_response.json()["status"] == "processed"

    with Session(engine) as session:
        second_prisoner = session.query(Prisoner).filter(Prisoner.source_ip == "203.0.113.11").one()
        assert second_prisoner.enrichment_status == "pending"
        assert second_prisoner.enrichment_reason_metadata == {
            "country_code": "pending",
            "asn": "pending",
            "reputation": "pending",
        }
