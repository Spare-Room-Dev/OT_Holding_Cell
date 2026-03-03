"""Auth boundary tests for ingest endpoint."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _forwarded_ip(ip: str) -> dict[str, str]:
    return {"X-Forwarded-For": ip}


def _ingest_payload() -> dict[str, object]:
    return {
        "delivery_id": str(uuid4()),
        "protocol": "ssh",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "credentials": ["root:toor"],
        "commands": ["whoami"],
        "downloads": ["http://example.invalid/dropper.bin"],
    }


def test_ingest_accepts_allowlisted_ip_with_valid_bearer(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        headers={**_auth_headers("current-forwarder-key"), **_forwarded_ip("203.0.113.10")},
        json=_ingest_payload(),
    )

    assert response.status_code == 200


def test_ingest_rejects_missing_bearer(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        headers=_forwarded_ip("203.0.113.10"),
        json=_ingest_payload(),
    )

    assert response.status_code == 401


def test_ingest_rejects_invalid_bearer(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        headers={**_auth_headers("wrong-key"), **_forwarded_ip("203.0.113.10")},
        json=_ingest_payload(),
    )

    assert response.status_code == 401


def test_ingest_rejects_disallowed_source_ip_with_valid_bearer(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        headers={**_auth_headers("current-forwarder-key"), **_forwarded_ip("198.51.100.77")},
        json=_ingest_payload(),
    )

    assert response.status_code == 403
