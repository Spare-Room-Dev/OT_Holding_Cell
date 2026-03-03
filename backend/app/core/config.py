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
