"""Canonical ingest mutation tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.prisoner import Prisoner
from app.models.prisoner_protocol_activity import PrisonerProtocolActivity
from app.schemas.ingest import IngestPayload
from app.services.ingest_service import process_ingest_payload


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _payload(
    *,
    protocol: str,
    timestamp: datetime,
    credentials: list[str],
    commands: list[str],
    downloads: list[str],
) -> IngestPayload:
    return IngestPayload.model_validate(
        {
            "delivery_id": str(uuid4()),
            "protocol": protocol,
            "timestamp": timestamp.isoformat(),
            "credentials": credentials,
            "commands": commands,
            "downloads": downloads,
        }
    )


def test_canonical_prisoner_aggregates_attempts_across_protocols(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'canonical-ingest.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    source_ip = "203.0.113.44"
    now = datetime.now(timezone.utc)

    first = _payload(
        protocol="ssh",
        timestamp=now,
        credentials=["root:toor"],
        commands=["uname -a"],
        downloads=["http://example.invalid/dropper.sh"],
    )
    second = _payload(
        protocol="telnet",
        timestamp=now + timedelta(seconds=1),
        credentials=["admin:admin"],
        commands=["cat /etc/passwd", "id"],
        downloads=["http://example.invalid/wget.bin"],
    )

    with SessionFactory() as session:
        first_result = process_ingest_payload(payload=first, source_ip=source_ip, session=session)
    with SessionFactory() as session:
        second_result = process_ingest_payload(payload=second, source_ip=source_ip, session=session)

    assert first_result["status"] == "processed"
    assert first_result["outcome"] == "created"
    assert second_result["status"] == "processed"
    assert second_result["outcome"] == "updated"
    assert second_result["prisoner_id"] == first_result["prisoner_id"]

    with Session(engine) as session:
        prisoner_rows = session.query(Prisoner).filter(Prisoner.source_ip == source_ip).all()
        assert len(prisoner_rows) == 1
        prisoner = prisoner_rows[0]

        assert prisoner.attempt_count == 2
        assert prisoner.credential_count == 2
        assert prisoner.command_count == 3
        assert prisoner.download_count == 2

        protocol_rows = (
            session.query(PrisonerProtocolActivity)
            .filter(PrisonerProtocolActivity.prisoner_id == prisoner.id)
            .order_by(PrisonerProtocolActivity.protocol.asc())
            .all()
        )

    assert [row.protocol for row in protocol_rows] == ["ssh", "telnet"]
    assert [row.attempt_count for row in protocol_rows] == [1, 1]
