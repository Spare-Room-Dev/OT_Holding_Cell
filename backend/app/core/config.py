"""Typed settings for backend security boundary."""

from __future__ import annotations

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
    ingest_rate_limit_max_requests: int = 120
    ingest_rate_limit_window_seconds: int = 60
    heartbeat_rate_limit_max_requests: int = 60
    heartbeat_rate_limit_window_seconds: int = 60
    heartbeat_stale_after_seconds: int = 300
    ingest_rate_limit_max_requests: int = 120
    ingest_rate_limit_window_seconds: int = 60
    heartbeat_rate_limit_max_requests: int = 120
    heartbeat_rate_limit_window_seconds: int = 60

    @field_validator("ingest_api_key_previous", mode="before")
    @classmethod
    def normalize_previous_key(cls, value: object) -> object:
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

    @field_validator(
        "ingest_rate_limit_max_requests",
        "ingest_rate_limit_window_seconds",
        "heartbeat_rate_limit_max_requests",
        "heartbeat_rate_limit_window_seconds",
        "heartbeat_stale_after_seconds",
    )
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Rate-limit and heartbeat windows must be positive integers")
        return value

    @field_validator(
        "ingest_rate_limit_max_requests",
        "ingest_rate_limit_window_seconds",
        "heartbeat_rate_limit_max_requests",
        "heartbeat_rate_limit_window_seconds",
    )
    @classmethod
    def ensure_positive_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Rate-limit settings must be greater than zero")
        return value

    def validate_boundary(self) -> None:
        if not self.ingest_api_key.get_secret_value().strip():
            raise ValueError("INGEST_API_KEY must be non-empty")

        if not self.allowed_forwarder_ips:
            raise ValueError("ALLOWED_FORWARDER_IPS must include at least one valid IP address")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_boundary()
    return settings
