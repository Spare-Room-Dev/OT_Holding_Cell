"""SQLAlchemy declarative base metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared ORM base for backend persistence models."""

