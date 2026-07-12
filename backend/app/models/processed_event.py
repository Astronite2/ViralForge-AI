"""Processed event persistence model."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin


class ProcessedEventModel(TimestampMixin, Base):
    """Record processed domain events for idempotency."""

    __tablename__ = "processed_events"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_processed_events_event_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
