"""Connected websocket registry and fanout delivery for realtime events."""

from __future__ import annotations

import asyncio

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.schemas.realtime import RealtimeEventEnvelope


class RealtimeConnectionManager:
    """Tracks connected sockets and broadcasts typed realtime envelopes."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: set[WebSocket] = set()

    async def register(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, envelope: RealtimeEventEnvelope) -> None:
        serialized = envelope.model_dump(mode="json")
        async with self._lock:
            targets = list(self._connections)

        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(serialized)
            except (RuntimeError, WebSocketDisconnect):
                stale.append(websocket)

        if stale:
            async with self._lock:
                for websocket in stale:
                    self._connections.discard(websocket)
