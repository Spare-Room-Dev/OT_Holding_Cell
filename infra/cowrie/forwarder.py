#!/usr/bin/env python3
"""Cowrie -> Holding Cell forwarder for Hetzner-hosted honeypots.

Tails Cowrie JSON logs, groups activity per session, and posts normalized payloads
to the backend ingest endpoint with retry/dead-letter behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import random
import signal
import time
from typing import Any, Optional
from uuid import uuid4

import requests


LOG = logging.getLogger("holding-cell-forwarder")

CONNECT_EVENT = "cowrie.session.connect"
CLOSE_EVENT = "cowrie.session.closed"
LOGIN_EVENTS = {"cowrie.login.success", "cowrie.login.failed"}
COMMAND_EVENTS = {"cowrie.command.input", "cowrie.command.failed"}
DOWNLOAD_EVENTS = {"cowrie.session.file_download"}
RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_bool(raw_value: str | None, *, default: bool) -> bool:
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_float(raw_value: str | None, *, default: float) -> float:
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _parse_int(raw_value: str | None, *, default: int) -> int:
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _parse_timestamp(raw_value: Any) -> datetime:
    if not isinstance(raw_value, str) or raw_value.strip() == "":
        return _utc_now()
    normalized = raw_value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return _utc_now()

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _truncate(value: Any, limit: int) -> str:
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit]


@dataclass(frozen=True)
class ForwarderConfig:
    backend_base_url: str
    ingest_api_key: str
    cowrie_log_path: Path
    state_path: Path
    dead_letter_path: Path
    poll_interval_seconds: float
    heartbeat_interval_seconds: int
    heartbeat_protocols: tuple[str, ...]
    session_idle_timeout_seconds: int
    session_max_duration_seconds: int
    session_max_events: int
    request_timeout_seconds: int
    max_retries: int
    backoff_base_seconds: float
    start_from_end: bool
    verify_tls: bool

    @classmethod
    def from_env(cls) -> "ForwarderConfig":
        backend_base_url = os.getenv("HC_BACKEND_BASE_URL", "").strip()
        ingest_api_key = os.getenv("HC_INGEST_API_KEY", "").strip()
        if not backend_base_url:
            raise ValueError("HC_BACKEND_BASE_URL is required")
        if not ingest_api_key:
            raise ValueError("HC_INGEST_API_KEY is required")

        protocols = [
            item.strip().lower()
            for item in os.getenv("HC_HEARTBEAT_PROTOCOLS", "ssh,telnet").split(",")
            if item.strip()
        ]
        heartbeat_protocols = tuple(protocol for protocol in protocols if protocol in {"ssh", "telnet"})
        if not heartbeat_protocols:
            heartbeat_protocols = ("ssh",)

        return cls(
            backend_base_url=backend_base_url.rstrip("/"),
            ingest_api_key=ingest_api_key,
            cowrie_log_path=Path(os.getenv("HC_COWRIE_LOG_PATH", "/var/log/cowrie/cowrie.json")),
            state_path=Path(os.getenv("HC_STATE_PATH", "/var/lib/holding-cell/forwarder-state.json")),
            dead_letter_path=Path(os.getenv("HC_DEAD_LETTER_PATH", "/var/log/holding-cell/dead_letter.jsonl")),
            poll_interval_seconds=max(_parse_float(os.getenv("HC_POLL_INTERVAL_SECONDS"), default=1.0), 0.1),
            heartbeat_interval_seconds=max(
                _parse_int(os.getenv("HC_HEARTBEAT_INTERVAL_SECONDS"), default=300),
                30,
            ),
            heartbeat_protocols=heartbeat_protocols,
            session_idle_timeout_seconds=max(
                _parse_int(os.getenv("HC_SESSION_IDLE_TIMEOUT_SECONDS"), default=30),
                5,
            ),
            session_max_duration_seconds=max(
                _parse_int(os.getenv("HC_SESSION_MAX_DURATION_SECONDS"), default=300),
                30,
            ),
            session_max_events=max(_parse_int(os.getenv("HC_SESSION_MAX_EVENTS"), default=100), 10),
            request_timeout_seconds=max(_parse_int(os.getenv("HC_REQUEST_TIMEOUT_SECONDS"), default=10), 3),
            max_retries=max(_parse_int(os.getenv("HC_MAX_RETRIES"), default=3), 0),
            backoff_base_seconds=max(
                _parse_float(os.getenv("HC_BACKOFF_BASE_SECONDS"), default=2.0),
                0.25,
            ),
            start_from_end=_parse_bool(os.getenv("HC_START_FROM_END"), default=True),
            verify_tls=_parse_bool(os.getenv("HC_VERIFY_TLS"), default=True),
        )


@dataclass
class SessionBuffer:
    session_id: str
    source_ip: str
    source_port: int
    dest_port: int
    protocol: str
    started_at: datetime
    last_event_at: datetime
    credentials: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    downloads: list[str] = field(default_factory=list)
    event_count: int = 0
    is_complete: bool = False


class CowrieForwarder:
    def __init__(self, config: ForwarderConfig) -> None:
        self.config = config
        self.stop_requested = False
        self.sessions: dict[str, SessionBuffer] = {}
        self.http = requests.Session()
        self.log_handle: Optional[Any] = None
        self.log_inode: Optional[int] = None
        self.log_offset = 0
        self.next_heartbeat_at = _utc_now() + timedelta(seconds=5)

        self._ensure_parent_dirs()
        self._load_state()
        self._install_signal_handlers()

    def _ensure_parent_dirs(self) -> None:
        self.config.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.dead_letter_path.parent.mkdir(parents=True, exist_ok=True)

    def _install_signal_handlers(self) -> None:
        def _handle_signal(_signum: int, _frame: Any) -> None:
            LOG.info("stop_requested")
            self.stop_requested = True

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    def _load_state(self) -> None:
        if not self.config.state_path.exists():
            return
        try:
            payload = json.loads(self.config.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            LOG.warning("state_load_failed")
            return

        self.log_offset = int(payload.get("offset", 0))
        self.log_inode = int(payload["inode"]) if "inode" in payload else None

    def _persist_state(self) -> None:
        payload = {
            "offset": self.log_offset,
            "inode": self.log_inode,
            "updated_at": _utc_now().isoformat(),
        }
        self.config.state_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _refresh_log_handle(self) -> None:
        if not self.config.cowrie_log_path.exists():
            return

        stat_result = self.config.cowrie_log_path.stat()
        current_inode = stat_result.st_ino

        must_reopen = self.log_handle is None
        if self.log_inode is not None and self.log_inode != current_inode:
            must_reopen = True
            self.log_offset = 0
        elif stat_result.st_size < self.log_offset:
            must_reopen = True
            self.log_offset = 0

        if not must_reopen:
            return

        if self.log_handle is not None:
            self.log_handle.close()

        self.log_handle = self.config.cowrie_log_path.open("rb")
        self.log_inode = current_inode

        if self.log_offset == 0 and self.config.start_from_end and not self.config.state_path.exists():
            self.log_handle.seek(0, os.SEEK_END)
            self.log_offset = self.log_handle.tell()
            self._persist_state()
            LOG.info("initialized_from_end", extra={"offset": self.log_offset})
            return

        self.log_handle.seek(self.log_offset)

    def _drain_log(self) -> None:
        if self.log_handle is None:
            return

        self.log_handle.seek(self.log_offset)
        while True:
            raw_line = self.log_handle.readline()
            if not raw_line:
                break

            self.log_offset = self.log_handle.tell()
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                LOG.warning("invalid_json_line")
                continue
            self._process_event(event)

        self._persist_state()

    def _process_event(self, event: dict[str, Any]) -> None:
        if event.get("isError") == 1:
            return

        session_id = str(event.get("session") or "").strip()
        if not session_id:
            return

        event_id = str(event.get("eventid") or "").strip()
        event_time = _parse_timestamp(event.get("timestamp"))
        session = self._ensure_session(session_id=session_id, event=event, event_time=event_time)
        session.last_event_at = event_time
        session.event_count += 1

        if event_id in LOGIN_EVENTS:
            username = _truncate(event.get("username", ""), 128)
            password = _truncate(event.get("password", ""), 128)
            if username or password:
                combined = f"{username}:{password}" if password else username
                session.credentials.append(_truncate(combined, 256))

        if event_id in COMMAND_EVENTS:
            command = _truncate(event.get("input", ""), 2048)
            if command:
                session.commands.append(command)

        if event_id in DOWNLOAD_EVENTS:
            url = _truncate(event.get("url", ""), 2048)
            if url:
                session.downloads.append(url)

        if event_id == CLOSE_EVENT:
            session.is_complete = True
            self._flush_session(session_id=session.session_id, reason="session_closed")
            return

        if session.event_count >= self.config.session_max_events:
            self._flush_session(session_id=session.session_id, reason="event_cap")

    def _ensure_session(self, *, session_id: str, event: dict[str, Any], event_time: datetime) -> SessionBuffer:
        existing = self.sessions.get(session_id)
        if existing is not None:
            return existing

        source_ip = _truncate(event.get("src_ip", "0.0.0.0"), 64)
        source_port = _parse_int(str(event.get("src_port", "0")), default=0)
        dest_port = _parse_int(str(event.get("dst_port", "22")), default=22)
        protocol = str(event.get("protocol", "")).strip().lower()
        if protocol not in {"ssh", "telnet"}:
            protocol = "telnet" if dest_port in {23, 2323} else "ssh"

        created = SessionBuffer(
            session_id=session_id,
            source_ip=source_ip,
            source_port=source_port,
            dest_port=dest_port,
            protocol=protocol,
            started_at=event_time,
            last_event_at=event_time,
        )
        self.sessions[session_id] = created
        return created

    def _flush_due_sessions(self) -> None:
        if not self.sessions:
            return

        now = _utc_now()
        to_flush: list[tuple[str, str]] = []
        idle_cutoff = timedelta(seconds=self.config.session_idle_timeout_seconds)
        max_duration = timedelta(seconds=self.config.session_max_duration_seconds)

        for session_id, session in self.sessions.items():
            if now - session.last_event_at >= idle_cutoff:
                to_flush.append((session_id, "idle_timeout"))
                continue
            if now - session.started_at >= max_duration:
                to_flush.append((session_id, "max_duration"))

        for session_id, reason in to_flush:
            self._flush_session(session_id=session_id, reason=reason)

    def _flush_session(self, *, session_id: str, reason: str) -> None:
        session = self.sessions.pop(session_id, None)
        if session is None:
            return

        payload = {
            "delivery_id": str(uuid4()),
            "protocol": session.protocol,
            "timestamp": _utc_now().isoformat(),
            "credentials": session.credentials[:100],
            "commands": session.commands[:200],
            "downloads": session.downloads[:100],
        }

        ok, error = self._post_with_retry(path="/api/ingest", payload=payload, write_dead_letter=True)
        if ok:
            LOG.info(
                "ingest_sent",
                extra={
                    "session_id": session.session_id,
                    "source_ip": session.source_ip,
                    "protocol": session.protocol,
                    "reason": reason,
                    "event_count": session.event_count,
                },
            )
        else:
            LOG.error(
                "ingest_failed",
                extra={
                    "session_id": session.session_id,
                    "source_ip": session.source_ip,
                    "reason": reason,
                    "error": error,
                },
            )

    def _post_with_retry(self, *, path: str, payload: dict[str, Any], write_dead_letter: bool) -> tuple[bool, str]:
        url = f"{self.config.backend_base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.config.ingest_api_key}",
            "Content-Type": "application/json",
        }
        attempts = self.config.max_retries + 1
        last_error = "unknown_error"

        for attempt in range(1, attempts + 1):
            try:
                response = self.http.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.config.request_timeout_seconds,
                    verify=self.config.verify_tls,
                )
            except requests.RequestException as exc:
                last_error = f"request_exception:{exc}"
                if attempt < attempts:
                    self._sleep_backoff(attempt)
                    continue
                break

            if response.status_code < 300:
                return True, ""

            last_error = f"http_{response.status_code}:{response.text[:250]}"
            if response.status_code in RETRIABLE_STATUS_CODES and attempt < attempts:
                self._sleep_backoff(attempt)
                continue
            break

        if write_dead_letter:
            self._append_dead_letter(payload=payload, error=last_error)
        return False, last_error

    def _sleep_backoff(self, attempt: int) -> None:
        delay = self.config.backoff_base_seconds * (2 ** max(attempt - 1, 0))
        jitter = random.uniform(0.0, 1.0)
        time.sleep(delay + jitter)

    def _append_dead_letter(self, *, payload: dict[str, Any], error: str) -> None:
        record = {
            "timestamp": _utc_now().isoformat(),
            "error": error,
            "payload": payload,
        }
        with self.config.dead_letter_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")

    def _send_heartbeat(self, protocol: str) -> None:
        payload = {
            "protocol": protocol,
            "timestamp": _utc_now().isoformat(),
        }
        ok, error = self._post_with_retry(path="/api/heartbeat", payload=payload, write_dead_letter=False)
        if ok:
            LOG.info("heartbeat_sent", extra={"protocol": protocol})
            return
        LOG.warning("heartbeat_failed", extra={"protocol": protocol, "error": error})

    def _maybe_send_heartbeat(self) -> None:
        now = _utc_now()
        if now < self.next_heartbeat_at:
            return
        for protocol in self.config.heartbeat_protocols:
            self._send_heartbeat(protocol)
        self.next_heartbeat_at = now + timedelta(seconds=self.config.heartbeat_interval_seconds)

    def _flush_all_sessions(self) -> None:
        for session_id in list(self.sessions.keys()):
            self._flush_session(session_id=session_id, reason="shutdown")

    def run(self) -> None:
        LOG.info("forwarder_starting")
        while not self.stop_requested:
            try:
                self._refresh_log_handle()
                self._drain_log()
                self._flush_due_sessions()
                self._maybe_send_heartbeat()
            except Exception as exc:  # pragma: no cover - operational safety.
                LOG.exception("forwarder_loop_error", extra={"error": str(exc)})
            time.sleep(self.config.poll_interval_seconds)

        self._flush_all_sessions()
        if self.log_handle is not None:
            self.log_handle.close()
        LOG.info("forwarder_stopped")


def main() -> int:
    log_level = os.getenv("HC_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        config = ForwarderConfig.from_env()
    except ValueError as exc:
        LOG.error("invalid_configuration", extra={"error": str(exc)})
        return 2

    CowrieForwarder(config=config).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
