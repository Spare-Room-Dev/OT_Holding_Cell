"""Captured command history for a canonical prisoner."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.prisoner import Prisoner


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PrisonerCommand(Base):
    """Command entry with protocol and observed timestamp."""

    __tablename__ = "prisoner_commands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prisoner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prisoners.id", ondelete="CASCADE"),
        nullable=False,
    )
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    command: Mapped[str] = mapped_column(String(2048), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    prisoner: Mapped["Prisoner"] = relationship("Prisoner", back_populates="commands")
