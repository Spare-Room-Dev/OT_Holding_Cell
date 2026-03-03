"""Prisoner persistence model for ingest mutation tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.enrichment_job import EnrichmentJob
    from app.models.prisoner_command import PrisonerCommand
    from app.models.prisoner_credential import PrisonerCredential
    from app.models.prisoner_download import PrisonerDownload
    from app.models.prisoner_protocol_activity import PrisonerProtocolActivity


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Prisoner(Base):
    """Represents canonical attacker identity keyed by source IP."""

    __tablename__ = "prisoners"
    __table_args__ = (UniqueConstraint("source_ip", name="uq_prisoner_source_ip"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ip: Mapped[str] = mapped_column(String(64), nullable=False)
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    credential_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    command_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enrichment_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    enrichment_country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    enrichment_asn: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    enrichment_reputation_severity: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    enrichment_reputation_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enrichment_reason_metadata: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    enrichment_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    protocol_activities: Mapped[list["PrisonerProtocolActivity"]] = relationship(
        "PrisonerProtocolActivity",
        back_populates="prisoner",
        cascade="all, delete-orphan",
    )
    credentials: Mapped[list["PrisonerCredential"]] = relationship(
        "PrisonerCredential",
        back_populates="prisoner",
        cascade="all, delete-orphan",
    )
    commands: Mapped[list["PrisonerCommand"]] = relationship(
        "PrisonerCommand",
        back_populates="prisoner",
        cascade="all, delete-orphan",
    )
    downloads: Mapped[list["PrisonerDownload"]] = relationship(
        "PrisonerDownload",
        back_populates="prisoner",
        cascade="all, delete-orphan",
    )
    enrichment_jobs: Mapped[list["EnrichmentJob"]] = relationship(
        "EnrichmentJob",
        back_populates="prisoner",
        cascade="all, delete-orphan",
    )
