"""Typed settings for backend security boundary."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal, Optional

from pydantic import IPvAnyAddress, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["test", "development", "production"] = "test"
    ingest_api_key: SecretStr = SecretStr("test-ingest-key")
    ingest_api_key_previous: Optional[SecretStr] = None
    allowed_forwarder_ips: tuple[IPvAnyAddress, ...] = ("127.0.0.1",)
    approved_browser_origins: tuple[str, ...] = ("http://localhost:5173",)
    approved_backend_connect_src: tuple[str, ...] = (
        "https://api.holdingcell.test",
        "wss://api.holdingcell.test",
    )
    ingest_rate_limit_max_requests: int = 120
    ingest_rate_limit_window_seconds: int = 60
    heartbeat_rate_limit_max_requests: int = 60
    heartbeat_rate_limit_window_seconds: int = 60
    heartbeat_stale_warning_seconds: int = 300
    enrichment_provider_timeout_seconds: int = 8
    ipinfo_token: Optional[SecretStr] = None
    abuseipdb_api_key: Optional[SecretStr] = None
    enrichment_retry_max_attempts: int = 3
    enrichment_retry_min_backoff_seconds: int = 30
    enrichment_retry_max_backoff_seconds: int = 900
    enrichment_quota_backoff_seconds: int = 120
    realtime_protocol_version: str = "v1"
    realtime_stats_cadence_ms: int = 1000
    credential_history_cap: int = 200
    command_history_cap: int = 400
    download_history_cap: int = 150
    retention_prisoner_days: int = 30
    retention_delivery_days: int = 7

    @field_validator("ingest_api_key_previous", mode="before")
    @classmethod
    def normalize_previous_key(cls, value: object) -> object:
        if value in (None, "", " "):
            return None
        return value

    @field_validator("ipinfo_token", "abuseipdb_api_key", mode="before")
    @classmethod
    def normalize_optional_secrets(cls, value: object) -> object:
        if value in (None, "", " "):
            return None
        return value

    @field_validator("allowed_forwarder_ips", mode="before")
    @classmethod
    def parse_allowed_ips(cls, value: object) -> object:
        if isinstance(value, str):
            parsed = tuple(ip.strip() for ip in value.split(",") if ip.strip())
            return parsed
        return value

    @field_validator("approved_browser_origins", "approved_backend_connect_src", mode="before")
    @classmethod
    def parse_origin_lists(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        raw = value.strip()
        if not raw:
            return ()

        if raw.startswith("["):
            try:
                parsed_json = json.loads(raw)
                if isinstance(parsed_json, list):
                    return tuple(str(item).strip() for item in parsed_json if str(item).strip())
            except json.JSONDecodeError:
                pass

        return tuple(item.strip() for item in raw.split(",") if item.strip())

    @field_validator(
        "ingest_rate_limit_max_requests",
        "ingest_rate_limit_window_seconds",
        "heartbeat_rate_limit_max_requests",
        "heartbeat_rate_limit_window_seconds",
        "heartbeat_stale_warning_seconds",
        "enrichment_provider_timeout_seconds",
        "enrichment_retry_max_attempts",
        "enrichment_retry_min_backoff_seconds",
        "enrichment_retry_max_backoff_seconds",
        "enrichment_quota_backoff_seconds",
        "realtime_stats_cadence_ms",
    )
    @classmethod
    def ensure_positive_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Rate limits, heartbeat, and enrichment settings must be positive integers")
        return value

    def validate_origin_policy(self) -> None:
        if not self.approved_browser_origins:
            raise ValueError("APPROVED_BROWSER_ORIGINS must include at least one origin")

        if self.app_env != "development" and "*" in self.approved_browser_origins:
            raise ValueError("Wildcard approved origins are only allowed in development mode")

    @field_validator(
        "credential_history_cap",
        "command_history_cap",
        "download_history_cap",
    )
    @classmethod
    def ensure_positive_history_caps(cls, value: int) -> int:
        if value < 1:
            raise ValueError("History caps must be greater than zero")
        return value

    @field_validator(
        "retention_prisoner_days",
        "retention_delivery_days",
    )
    @classmethod
    def ensure_positive_retention_windows(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Retention windows must be greater than zero")
        return value

    def validate_boundary(self) -> None:
        if not self.ingest_api_key.get_secret_value().strip():
            raise ValueError("INGEST_API_KEY must be non-empty")

        if not self.allowed_forwarder_ips:
            raise ValueError("ALLOWED_FORWARDER_IPS must include at least one valid IP address")

        self.validate_origin_policy()


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_boundary()
    return settings
