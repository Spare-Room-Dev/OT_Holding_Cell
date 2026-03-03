"""Replay-safety tests for ingest delivery idempotency."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from app.models.ingest_delivery import IngestDelivery
from app.models.prisoner import Prisoner
from app.models.prisoner_protocol_activity import PrisonerProtocolActivity


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _trusted_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer current-forwarder-key",
        "X-Forwarded-For": "203.0.113.10",
    }


def _valid_ingest_payload() -> dict[str, object]:
    return {
        "delivery_id": str(uuid4()),
        "protocol": "ssh",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "credentials": ["root:toor"],
        "commands": ["whoami"],
        "downloads": ["http://example.invalid/malware.bin"],
    }


def test_migration_enforces_unique_delivery_id(tmp_path: Path) -> None:
    database_path = tmp_path / "ingest-idempotency.sqlite3"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        session.add(
            IngestDelivery(
                delivery_id="delivery-001",
                source_ip="203.0.113.10",
                protocol="ssh",
            )
        )
        session.commit()

        session.add(
            IngestDelivery(
                delivery_id="delivery-001",
                source_ip="203.0.113.10",
                protocol="ssh",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_migration_creates_ingest_delivery_metadata_columns(tmp_path: Path) -> None:
    database_path = tmp_path / "ingest-idempotency.sqlite3"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    schema = inspect(engine)

    columns = {column["name"] for column in schema.get_columns("ingest_deliveries")}
    assert columns == {
        "id",
        "delivery_id",
        "protocol",
        "source_ip",
        "prisoner_id",
        "created_at",
    }

    unique_constraints = schema.get_unique_constraints("ingest_deliveries")
    assert any(
        constraint["name"] == "uq_ingest_delivery_id" and constraint["column_names"] == ["delivery_id"]
        for constraint in unique_constraints
    )

    foreign_keys = schema.get_foreign_keys("ingest_deliveries")
    assert any(
        foreign_key["referred_table"] == "prisoners"
        and foreign_key["constrained_columns"] == ["prisoner_id"]
        and foreign_key["referred_columns"] == ["id"]
        for foreign_key in foreign_keys
    )


@pytest.fixture
def idempotency_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str]:
    database_path = tmp_path / "idempotency-api.sqlite3"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(_alembic_config(database_url), "head")

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("INGEST_API_KEY", "current-forwarder-key")
    monkeypatch.setenv("INGEST_API_KEY_PREVIOUS", "previous-forwarder-key")
    monkeypatch.setenv("ALLOWED_FORWARDER_IPS", "[\"203.0.113.10\", \"127.0.0.1\"]")

    from app.core.config import get_settings
    from app.db.session import create_session_factory
    from app.main import create_app
    import app.db.session as db_session_module

    get_settings.cache_clear()
    db_session_module.SessionFactory = create_session_factory(database_url)
    return TestClient(create_app()), database_url


def test_duplicate_delivery_returns_duplicate_ignored_and_skips_mutation(
    idempotency_client: tuple[TestClient, str],
) -> None:
    client, database_url = idempotency_client
    payload = _valid_ingest_payload()

    first_response = client.post("/api/ingest", headers=_trusted_headers(), json=payload)
    duplicate_response = client.post("/api/ingest", headers=_trusted_headers(), json=payload)

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "processed"
    assert first_response.json()["outcome"] == "created"

    assert duplicate_response.status_code == 200
    assert duplicate_response.json() == {
        "status": "duplicate_ignored",
        "delivery_id": payload["delivery_id"],
    }

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        prisoner_count = session.query(Prisoner).count()
        delivery_count = session.query(IngestDelivery).count()
        prisoner = session.query(Prisoner).one()

    assert prisoner_count == 1
    assert delivery_count == 1
    assert prisoner.attempt_count == 1
    assert prisoner.credential_count == 1
    assert prisoner.command_count == 1
    assert prisoner.download_count == 1

    protocol_activities = (
        session.query(PrisonerProtocolActivity)
        .filter(PrisonerProtocolActivity.prisoner_id == prisoner.id)
        .all()
    )
    assert len(protocol_activities) == 1
    assert protocol_activities[0].attempt_count == 1


def test_parallel_duplicate_submissions_mutate_once(tmp_path: Path) -> None:
    database_path = tmp_path / "idempotency-concurrency.sqlite3"
    database_url = f"sqlite:///{database_path}"

    command.upgrade(_alembic_config(database_url), "head")

    payload = _valid_ingest_payload()
    source_ip = "203.0.113.10"

    SessionFactory = sessionmaker(bind=create_engine(database_url, future=True), expire_on_commit=False, class_=Session)

    def _submit_once() -> dict[str, object]:
        from app.schemas.ingest import IngestPayload
        from app.services.ingest_service import process_ingest_payload

        with SessionFactory() as session:
            return process_ingest_payload(
                payload=IngestPayload.model_validate(payload),
                source_ip=source_ip,
                session=session,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(lambda _: _submit_once(), range(2)))

    statuses = sorted([first["status"], second["status"]])
    assert statuses == ["duplicate_ignored", "processed"]

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        prisoner_count = session.query(Prisoner).count()
        delivery_count = session.query(IngestDelivery).count()
        prisoner = session.query(Prisoner).one()
        protocol_activities = (
            session.query(PrisonerProtocolActivity)
            .filter(PrisonerProtocolActivity.prisoner_id == prisoner.id)
            .all()
        )

    assert prisoner_count == 1
    assert delivery_count == 1
    assert prisoner.attempt_count == 1
    assert len(protocol_activities) == 1
    assert protocol_activities[0].attempt_count == 1
