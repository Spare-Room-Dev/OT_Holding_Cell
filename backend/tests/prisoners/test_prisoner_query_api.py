"""Prisoner query API behavior tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import app.db.session as db_session_module
from app.models.prisoner import Prisoner


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
