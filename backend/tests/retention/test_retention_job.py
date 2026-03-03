"""Retention lifecycle automation tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.ingest_delivery import IngestDelivery
from app.models.lifetime_rollup import LifetimeRollup
from app.models.prisoner import Prisoner
from app.models.retention_run import RetentionRun
from app.services.retention_service import run_retention_cycle


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_retention_purges_cutoff_rows_and_preserves_rollups(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'retention.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
    expired_seen_at = now - timedelta(days=31)
    fresh_seen_at = now - timedelta(days=3)

    with session_factory() as session:
        old_us = Prisoner(
            source_ip="203.0.113.10",
            country_code="US",
            attempt_count=5,
            first_seen_at=expired_seen_at - timedelta(hours=2),
            last_seen_at=expired_seen_at,
            credential_count=2,
            command_count=1,
            download_count=0,
        )
        old_unknown = Prisoner(
            source_ip="203.0.113.11",
            country_code=None,
            attempt_count=2,
            first_seen_at=expired_seen_at - timedelta(hours=1),
            last_seen_at=expired_seen_at,
            credential_count=0,
            command_count=1,
            download_count=1,
        )
        fresh = Prisoner(
            source_ip="203.0.113.12",
            country_code="DE",
            attempt_count=4,
            first_seen_at=fresh_seen_at - timedelta(hours=1),
            last_seen_at=fresh_seen_at,
            credential_count=1,
            command_count=1,
            download_count=1,
        )
        session.add_all([old_us, old_unknown, fresh])
        session.flush()

        session.add_all(
            [
                IngestDelivery(
                    delivery_id=str(uuid4()),
                    protocol="ssh",
                    source_ip=old_us.source_ip,
                    prisoner_id=old_us.id,
                    created_at=now - timedelta(days=8),
                ),
                IngestDelivery(
                    delivery_id=str(uuid4()),
                    protocol="telnet",
                    source_ip=fresh.source_ip,
                    prisoner_id=fresh.id,
                    created_at=now - timedelta(days=1),
                ),
            ]
        )
        session.commit()

    with session_factory() as session:
        first_run = run_retention_cycle(session=session, now=now)

    assert first_run["status"] == "succeeded"
    assert first_run["deleted_prisoner_count"] == 2
    assert first_run["deleted_delivery_count"] == 1

    with session_factory() as session:
        remaining_prisoners = session.query(Prisoner).order_by(Prisoner.source_ip.asc()).all()
        assert [row.source_ip for row in remaining_prisoners] == ["203.0.113.12"]

        remaining_deliveries = session.query(IngestDelivery).order_by(IngestDelivery.created_at.asc()).all()
        assert len(remaining_deliveries) == 1
        assert remaining_deliveries[0].source_ip == "203.0.113.12"

        rollups = {row.rollup_key: row.attempt_count for row in session.query(LifetimeRollup).all()}
        assert rollups["overall"] == 7
        assert rollups["country:US"] == 5
        assert rollups["country:UNKNOWN"] == 2

    with session_factory() as session:
        second_run = run_retention_cycle(session=session, now=now)

    assert second_run["status"] == "succeeded"
    assert second_run["deleted_prisoner_count"] == 0
    assert second_run["deleted_delivery_count"] == 0

    with session_factory() as session:
        rollups = {row.rollup_key: row.attempt_count for row in session.query(LifetimeRollup).all()}
        assert rollups["overall"] == 7
        assert rollups["country:US"] == 5
        assert rollups["country:UNKNOWN"] == 2

        runs = session.query(RetentionRun).order_by(RetentionRun.id.asc()).all()
        assert len(runs) == 2
        assert all(run.status == "succeeded" for run in runs)
