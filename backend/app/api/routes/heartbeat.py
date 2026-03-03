"""Forwarder heartbeat routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.rate_limit import require_heartbeat_rate_limit
from app.db.session import get_db_session
from app.schemas.heartbeat import HeartbeatPayload
from app.security.forwarder_auth import require_trusted_forwarder, resolve_client_ip
from app.services.heartbeat_service import record_heartbeat

router = APIRouter()


@router.post(
    "/heartbeat",
    status_code=200,
    dependencies=[Depends(require_trusted_forwarder), Depends(require_heartbeat_rate_limit)],
)
async def heartbeat(
    payload: HeartbeatPayload,
    request: Request,
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return record_heartbeat(
        session=session,
        source_ip=resolve_client_ip(request),
        protocol=payload.protocol,
        observed_at=payload.timestamp,
        warning_window_seconds=settings.heartbeat_stale_warning_seconds,
    )
