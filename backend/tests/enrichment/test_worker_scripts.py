"""CLI contracts for enrichment queue worker scripts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.prisoner import Prisoner
from app.services.enrichment_queue_service import enqueue_prisoner_enrichment


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _seed_pending_prisoner(*, session: Session, source_ip: str) -> int:
    now = datetime.now(timezone.utc)
    prisoner = Prisoner(
        source_ip=source_ip,
        country_code=None,
        attempt_count=1,
        first_seen_at=now,
        last_seen_at=now,
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
    return prisoner.id


def test_run_enrichment_drain_script_outputs_json_summary(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'enrichment-drain.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

    with session_factory() as session:
        prisoner_id = _seed_pending_prisoner(session=session, source_ip="203.0.113.50")
        enqueue_prisoner_enrichment(session=session, prisoner_id=prisoner_id)

    backend_root = Path(__file__).resolve().parents[2]
    script_path = backend_root / "scripts" / "run_enrichment_drain.py"

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(backend_root)
    env["ENRICHMENT_RETRY_MAX_ATTEMPTS"] = "1"
    env.pop("IPINFO_TOKEN", None)
    env.pop("ABUSEIPDB_API_KEY", None)

    result = subprocess.run(
        [sys.executable, str(script_path), "--batch-size", "10"],
        cwd=backend_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout.strip())
    assert summary["status"] == "succeeded"
    assert summary["claimed_count"] == 1
    assert summary["processed_count"] == 1
    assert summary["failed_count"] == 1


def test_run_enrichment_worker_script_loops_and_reports_fatal_errors(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'enrichment-worker.sqlite3'}"
    command.upgrade(_alembic_config(database_url), "head")

    backend_root = Path(__file__).resolve().parents[2]
    script_path = backend_root / "scripts" / "run_enrichment_worker.py"

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(backend_root)

    first = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--batch-size",
            "5",
            "--poll-interval-seconds",
            "0",
            "--max-loops",
            "1",
        ],
        cwd=backend_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert first.returncode == 0, first.stderr
    first_summary = json.loads(first.stdout.strip())
    assert first_summary["status"] == "succeeded"
    assert first_summary["loops"] == 1

    bad_env = env.copy()
    bad_env["DATABASE_URL"] = "unknown+driver://bad-url"

    second = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--batch-size",
            "1",
            "--poll-interval-seconds",
            "0",
            "--max-loops",
            "1",
        ],
        cwd=backend_root,
        env=bad_env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert second.returncode == 1
    second_summary = json.loads(second.stdout.strip())
    assert second_summary["status"] == "failed"
    assert second_summary["error"]
