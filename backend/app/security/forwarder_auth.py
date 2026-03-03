"""Shared trusted-forwarder authentication dependency."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


def _is_valid_key(token: str, settings: Settings) -> bool:
    valid_keys = {settings.ingest_api_key.get_secret_value()}
    if settings.ingest_api_key_previous is not None:
        valid_keys.add(settings.ingest_api_key_previous.get_secret_value())
    return token in valid_keys


def resolve_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return ""


def _is_allowlisted_ip(raw_ip: str, settings: Settings) -> bool:
    try:
        source_ip = ip_address(raw_ip)
    except ValueError:
        return False

    allowed = {str(ip) for ip in settings.allowed_forwarder_ips}
    return str(source_ip) in allowed


async def require_trusted_forwarder(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _is_valid_key(credentials.credentials, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _is_allowlisted_ip(resolve_client_ip(request), settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Source IP not allowed",
        )
