"""Websocket route, origin policy checks, and reconnect sync lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, WebSocket

from app.core.config import Settings
from app.core.config import get_settings
import app.db.session as db_session_module
from app.realtime.connection_manager import RealtimeConnectionManager
from app.realtime.event_bus import get_realtime_event_bus
from app.realtime.snapshot_service import build_authoritative_snapshot
from app.schemas.realtime import RealtimeEventEnvelope, RealtimeEventName

logger = logging.getLogger(__name__)

SOCKET_POLICY_VIOLATION_CODE = 1008
SYNC_ROUTE = "/ws/events"

router = APIRouter()
realtime_event_bus = get_realtime_event_bus()
connection_manager = RealtimeConnectionManager()
realtime_event_bus.subscribe(connection_manager.broadcast)


def _normalize_origin(origin: str) -> str:
    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.netloc:
        return origin.strip().rstrip("/")
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def is_socket_origin_allowed(origin: str | None, settings: Settings) -> bool:
    if origin is None:
        return False
    normalized_origin = _normalize_origin(origin)
    allowed = {_normalize_origin(candidate) for candidate in settings.approved_browser_origins}
    return normalized_origin in allowed


class _ConnectionEnvelopeFactory:
    def __init__(self, *, protocol_version: str) -> None:
        self._protocol_version = protocol_version
        self._publish_sequence = 0

    def build(self, *, event: RealtimeEventName, payload: dict[str, object]) -> RealtimeEventEnvelope:
        occurred_at = datetime.now(timezone.utc)
        self._publish_sequence += 1

        payload_with_ordering = dict(payload)
        ordering = dict(payload_with_ordering.get("ordering", {}))
        ordering.setdefault("publish_sequence", self._publish_sequence)
        ordering.setdefault("source_updated_at", occurred_at)
        payload_with_ordering["ordering"] = ordering

        if event == "welcome":
            payload_with_ordering.setdefault("server_time", occurred_at)

        return RealtimeEventEnvelope(
            event_id=f"ws-{uuid4().hex}",
            event=event,
            occurred_at=occurred_at,
            protocol_version=self._protocol_version,
            payload=payload_with_ordering,
        )


async def _send_envelope(*, websocket: WebSocket, envelope: RealtimeEventEnvelope) -> None:
    await websocket.send_json(envelope.model_dump(mode="json"))


async def _drain_ignored_inbound_frames(*, websocket: WebSocket, origin: str | None) -> None:
    while True:
        message = await websocket.receive()
        message_type = message.get("type")
        if message_type == "websocket.disconnect":
            return

        text_payload = message.get("text")
        bytes_payload = message.get("bytes")
        if text_payload is not None or bytes_payload is not None:
            logger.info(
                "ignored_client_ws_message",
                extra={
                    "origin": origin,
                    "frame_type": "text" if text_payload is not None else "bytes",
                },
            )


@router.websocket(SYNC_ROUTE)
async def websocket_events(websocket: WebSocket) -> None:
    settings = get_settings()
    origin = websocket.headers.get("origin")
    if not is_socket_origin_allowed(origin, settings):
        await websocket.close(code=SOCKET_POLICY_VIOLATION_CODE)
        return

    await websocket.accept()
    envelope_factory = _ConnectionEnvelopeFactory(
        protocol_version=settings.realtime_protocol_version,
    )
    sync_id = f"sync-{uuid4().hex[:12]}"

    with db_session_module.SessionFactory() as session:
        snapshot = build_authoritative_snapshot(session=session)

    await _send_envelope(
        websocket=websocket,
        envelope=envelope_factory.build(
            event="welcome",
            payload={},
        ),
    )
    await _send_envelope(
        websocket=websocket,
        envelope=envelope_factory.build(
            event="sync_start",
            payload={
                "sync_id": sync_id,
                "estimated_total_chunks": len(snapshot.chunks),
            },
        ),
    )
    for chunk in snapshot.chunks:
        await _send_envelope(
            websocket=websocket,
            envelope=envelope_factory.build(
                event="snapshot_chunk",
                payload={
                    "sync_id": sync_id,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "prisoners": chunk.prisoners,
                },
            ),
        )
    await _send_envelope(
        websocket=websocket,
        envelope=envelope_factory.build(
            event="stats_update",
            payload=snapshot.stats_payload,
        ),
    )
    await _send_envelope(
        websocket=websocket,
        envelope=envelope_factory.build(
            event="sync_complete",
            payload={
                "sync_id": sync_id,
                "estimated_total_chunks": len(snapshot.chunks),
            },
        ),
    )

    await connection_manager.register(websocket)
    try:
        await _drain_ignored_inbound_frames(websocket=websocket, origin=origin)
    finally:
        await connection_manager.unregister(websocket)
