"""Realtime stats snapshot and broadcaster cadence tests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.lifetime_rollup import LifetimeRollup
from app.models.prisoner import Prisoner
from app.realtime.stats_broadcaster import RealtimeStatsBroadcaster
from app.services.realtime_stats_service import build_realtime_stats_snapshot


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


def test_realtime_stats_snapshot_includes_current_and_lifetime_counters(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'stats-snapshot.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    anchor = datetime(2026, 3, 4, 12, 0, tzinfo=timezone.utc)
    active_seen_at = anchor - timedelta(minutes=10)
    stale_seen_at = anchor - timedelta(hours=40)

    with session_factory() as session:
        session.add_all(
            [
                Prisoner(
                    source_ip="198.51.100.10",
                    country_code="US",
                    attempt_count=4,
                    first_seen_at=anchor - timedelta(days=2),
                    last_seen_at=active_seen_at,
                    credential_count=2,
                    command_count=3,
                    download_count=1,
                ),
                Prisoner(
                    source_ip="198.51.100.11",
                    country_code="AU",
                    attempt_count=3,
                    first_seen_at=anchor - timedelta(days=3),
                    last_seen_at=stale_seen_at,
                    credential_count=1,
                    command_count=1,
                    download_count=0,
                ),
                LifetimeRollup(
                    rollup_key="overall",
                    country_code=None,
                    attempt_count=9,
                    created_at=anchor - timedelta(days=1),
                    updated_at=anchor - timedelta(days=1),
                ),
            ]
        )
        session.commit()

    with session_factory() as session:
        snapshot = build_realtime_stats_snapshot(session=session, now=anchor)

    assert snapshot == {
        "total_prisoners": 2,
        "active_prisoners": 1,
        "lifetime_attempts": 16,
        "lifetime_credentials": 3,
        "lifetime_commands": 4,
        "lifetime_downloads": 1,
    }


def test_stats_broadcaster_emits_only_on_changed_snapshot_values(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'stats-broadcaster.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    anchor = datetime(2026, 3, 4, 12, 30, tzinfo=timezone.utc)
    with session_factory() as session:
        session.add(
            Prisoner(
                source_ip="198.51.100.20",
                country_code="US",
                attempt_count=1,
                first_seen_at=anchor - timedelta(hours=1),
                last_seen_at=anchor - timedelta(minutes=1),
                credential_count=0,
                command_count=0,
                download_count=0,
            )
        )
        session.commit()

    bus = _CaptureBus()

    async def scenario() -> None:
        broadcaster = RealtimeStatsBroadcaster(
            session_factory=session_factory,
            event_bus=bus,
            cadence_ms=10,
        )

        await broadcaster.start()
        await asyncio.sleep(0.04)
        assert len(bus.calls) == 1
        assert bus.calls[0][0] == "stats_update"
        assert bus.calls[0][1]["changed"] is True

        await asyncio.sleep(0.03)
        assert len(bus.calls) == 1

        with session_factory() as session:
            prisoner = session.query(Prisoner).where(Prisoner.source_ip == "198.51.100.20").one()
            prisoner.attempt_count = 2
            prisoner.last_seen_at = anchor + timedelta(minutes=1)
            session.commit()

        await asyncio.sleep(0.04)
        assert len(bus.calls) == 2
        assert bus.calls[1][0] == "stats_update"
        assert bus.calls[1][1]["lifetime_attempts"] == 2
        assert bus.calls[1][1]["changed"] is True

        await asyncio.sleep(0.03)
        assert len(bus.calls) == 2
        await broadcaster.stop()

    asyncio.run(scenario())
