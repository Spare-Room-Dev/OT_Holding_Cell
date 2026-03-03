"""Validation boundary tests for ingest payload contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


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


def test_schema_bounds_reject_overflow(client: TestClient) -> None:
    payload = _valid_ingest_payload()
    payload["credentials"] = [f"user{i}:password{i}" for i in range(101)]

    response = client.post("/api/ingest", headers=_trusted_headers(), json=payload)

    assert response.status_code == 422


def test_ingest_rejects_protocol_outside_allowlist(client: TestClient) -> None:
    payload = _valid_ingest_payload()
    payload["protocol"] = "http"

    response = client.post("/api/ingest", headers=_trusted_headers(), json=payload)

    assert response.status_code == 422


def test_ingest_rejects_stale_timestamp(client: TestClient) -> None:
    payload = _valid_ingest_payload()
    payload["timestamp"] = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()

    response = client.post("/api/ingest", headers=_trusted_headers(), json=payload)

    assert response.status_code == 422
