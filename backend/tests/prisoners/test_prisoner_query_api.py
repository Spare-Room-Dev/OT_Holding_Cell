"""Prisoner query API behavior tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import app.db.session as db_session_module
from app.models.prisoner import Prisoner
from app.models.prisoner_command import PrisonerCommand
from app.models.prisoner_credential import PrisonerCredential
from app.models.prisoner_download import PrisonerDownload
from app.models.prisoner_protocol_activity import PrisonerProtocolActivity


def _create_prisoner(
    *,
    source_ip: str,
    timestamp: datetime,
    country_code: str | None,
) -> int:
    with db_session_module.SessionFactory() as session:
        prisoner = Prisoner(
            source_ip=source_ip,
            country_code=country_code,
            attempt_count=1,
            first_seen_at=timestamp,
            last_seen_at=timestamp,
            credential_count=0,
            command_count=0,
            download_count=0,
        )
        session.add(prisoner)
        session.flush()
        session.commit()
        return prisoner.id


def _add_prisoner_detail_history(*, prisoner_id: int, anchor: datetime) -> None:
    with db_session_module.SessionFactory() as session:
        shared_last_seen = anchor - timedelta(minutes=1)
        shared_observed = anchor - timedelta(minutes=2)

        session.add(
            PrisonerProtocolActivity(
                prisoner_id=prisoner_id,
                protocol="ssh",
                attempt_count=2,
                first_seen_at=anchor - timedelta(hours=2),
                last_seen_at=shared_last_seen,
            )
        )
        session.add(
            PrisonerProtocolActivity(
                prisoner_id=prisoner_id,
                protocol="telnet",
                attempt_count=5,
                first_seen_at=anchor - timedelta(hours=3),
                last_seen_at=shared_last_seen,
            )
        )

        session.add(
            PrisonerCredential(
                prisoner_id=prisoner_id,
                protocol="ssh",
                credential="root:********",
                observed_at=anchor - timedelta(minutes=10),
            )
        )
        session.add(
            PrisonerCredential(
                prisoner_id=prisoner_id,
                protocol="telnet",
                credential="admin:********",
                observed_at=anchor - timedelta(minutes=5),
            )
        )

        session.add(
            PrisonerCommand(
                prisoner_id=prisoner_id,
                protocol="ssh",
                command="id",
                observed_at=shared_observed,
            )
        )
        session.add(
            PrisonerCommand(
                prisoner_id=prisoner_id,
                protocol="ssh",
                command="uname -a",
                observed_at=shared_observed,
            )
        )

        session.add(
            PrisonerDownload(
                prisoner_id=prisoner_id,
                protocol="ssh",
                download_url="http://malicious.example/older.sh",
                observed_at=anchor - timedelta(minutes=7),
            )
        )
        session.add(
            PrisonerDownload(
                prisoner_id=prisoner_id,
                protocol="ssh",
                download_url="http://malicious.example/newer.sh",
                observed_at=anchor - timedelta(minutes=4),
            )
        )

        session.commit()


def test_prisoner_list_cursor_is_deterministic_with_country_filters(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    us_id = _create_prisoner(
        source_ip="198.51.100.10",
        timestamp=now - timedelta(minutes=1),
        country_code="US",
    )
    unknown_newer_id = _create_prisoner(
        source_ip="198.51.100.20",
        timestamp=now - timedelta(minutes=1),
        country_code=None,
    )
    au_id = _create_prisoner(
        source_ip="198.51.100.30",
        timestamp=now - timedelta(minutes=2),
        country_code="AU",
    )
    unknown_older_id = _create_prisoner(
        source_ip="198.51.100.40",
        timestamp=now - timedelta(minutes=3),
        country_code=None,
    )

    first_page = client.get("/api/prisoners", params={"limit": 2})
    assert first_page.status_code == 200
    first_payload = first_page.json()

    expected_first_ids = sorted([us_id, unknown_newer_id], reverse=True)
    assert [row["id"] for row in first_payload["items"]] == expected_first_ids
    assert isinstance(first_payload["next_cursor"], str)
    assert first_payload["next_cursor"]

    second_page = client.get(
        "/api/prisoners",
        params={"limit": 2, "cursor": first_payload["next_cursor"]},
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert [row["id"] for row in second_payload["items"]] == [au_id, unknown_older_id]
    assert second_payload["next_cursor"] is None

    unknown_country_page = client.get(
        "/api/prisoners",
        params={"country": "unknown", "limit": 10},
    )
    assert unknown_country_page.status_code == 200
    unknown_payload = unknown_country_page.json()
    assert [row["id"] for row in unknown_payload["items"]] == [unknown_newer_id, unknown_older_id]
    assert all(row["country_code"] is None for row in unknown_payload["items"])

    us_country_page = client.get(
        "/api/prisoners",
        params={"country": "US", "limit": 10},
    )
    assert us_country_page.status_code == 200
    assert [row["id"] for row in us_country_page.json()["items"]] == [us_id]

    malformed_cursor_page = client.get("/api/prisoners", params={"cursor": "%%%"})
    assert malformed_cursor_page.status_code == 400
    assert malformed_cursor_page.json() == {"detail": "Invalid cursor token"}


def test_prisoner_detail_returns_sectioned_histories(client: TestClient) -> None:
    now = datetime.now(timezone.utc)
    prisoner_id = _create_prisoner(
        source_ip="198.51.100.99",
        timestamp=now - timedelta(minutes=15),
        country_code="DE",
    )
    _add_prisoner_detail_history(prisoner_id=prisoner_id, anchor=now)

    list_page = client.get("/api/prisoners", params={"limit": 10})
    assert list_page.status_code == 200
    list_item = next(row for row in list_page.json()["items"] if row["id"] == prisoner_id)
    assert "protocol_history" not in list_item
    assert "credentials" not in list_item
    assert "commands" not in list_item
    assert "downloads" not in list_item

    detail_response = client.get(f"/api/prisoners/{prisoner_id}")
    assert detail_response.status_code == 200
    payload = detail_response.json()

    assert set(payload.keys()) == {"prisoner", "protocol_history", "credentials", "commands", "downloads"}
    assert payload["prisoner"]["id"] == prisoner_id

    assert [row["protocol"] for row in payload["protocol_history"]] == ["telnet", "ssh"]
    assert [row["credential"] for row in payload["credentials"]] == ["admin:********", "root:********"]
    assert [row["command"] for row in payload["commands"]] == ["uname -a", "id"]
    assert [row["download_url"] for row in payload["downloads"]] == [
        "http://malicious.example/newer.sh",
        "http://malicious.example/older.sh",
    ]

    not_found = client.get("/api/prisoners/999999")
    assert not_found.status_code == 404
    assert not_found.json() == {"detail": "Prisoner not found"}
