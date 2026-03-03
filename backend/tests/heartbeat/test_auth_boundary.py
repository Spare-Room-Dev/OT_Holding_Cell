"""Auth boundary tests for heartbeat endpoint."""

from fastapi.testclient import TestClient


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _forwarded_ip(ip: str) -> dict[str, str]:
    return {"X-Forwarded-For": ip}


def test_heartbeat_accepts_allowlisted_ip_with_valid_bearer(client: TestClient) -> None:
    response = client.post(
        "/api/heartbeat",
        headers={**_auth_headers("current-forwarder-key"), **_forwarded_ip("203.0.113.10")},
    )

    assert response.status_code == 200


def test_heartbeat_rejects_missing_bearer(client: TestClient) -> None:
    response = client.post("/api/heartbeat", headers=_forwarded_ip("203.0.113.10"))

    assert response.status_code == 401


def test_heartbeat_rejects_invalid_bearer(client: TestClient) -> None:
    response = client.post(
        "/api/heartbeat",
        headers={**_auth_headers("invalid-key"), **_forwarded_ip("203.0.113.10")},
    )

    assert response.status_code == 401


def test_heartbeat_rejects_disallowed_source_ip_with_valid_bearer(client: TestClient) -> None:
    response = client.post(
        "/api/heartbeat",
        headers={**_auth_headers("current-forwarder-key"), **_forwarded_ip("198.51.100.77")},
    )

    assert response.status_code == 403
