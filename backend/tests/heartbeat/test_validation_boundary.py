"""Validation boundary tests for heartbeat payload contract."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient


def _trusted_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer current-forwarder-key",
        "X-Forwarded-For": "203.0.113.10",
    }


def _valid_heartbeat_payload() -> dict[str, str]:
    return {
        "protocol": "ssh",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def test_heartbeat_rejects_protocol_outside_allowlist(client: TestClient) -> None:
    payload = _valid_heartbeat_payload()
    payload["protocol"] = "http"

    response = client.post("/api/heartbeat", headers=_trusted_headers(), json=payload)

    assert response.status_code == 422
