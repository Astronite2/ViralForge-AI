"""Trend signal persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.evidence import EvidenceModel
    from backend.app.models.topic import Topic


class TrendSignalModel(TimestampMixin, Base):
    """Persisted normalized signal associated with a topic."""

    __tablename__ = "trend_signals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    topic_id: Mapped[str | None] = mapped_column(
        ForeignKey("topics.id"), nullable=True, index=True
    )
    content_id: Mapped[str | None] = mapped_column(
        ForeignKey("content.id"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(100), index=True)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reason: Mapped[str] = mapped_column(String(500))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    topic: Mapped[Topic | None] = relationship(back_populates="signals")
    evidence: Mapped[list[EvidenceModel]] = relationship(back_populates="signal")
