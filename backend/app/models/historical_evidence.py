"""Historical evidence persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.historical_observation import HistoricalObservationModel


class HistoricalEvidenceModel(TimestampMixin, Base):
    """Persisted historical snapshot of decision evidence."""

    __tablename__ = "historical_evidence"
    __table_args__ = (
        UniqueConstraint("evidence_id", name="uq_historical_evidence_evidence_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id"), nullable=False, index=True
    )
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("historical_observations.id"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidence.id"), nullable=False, index=True
    )
    signal_id: Mapped[str] = mapped_column(
        ForeignKey("trend_signals.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    factor: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_value: Mapped[float] = mapped_column(Float, nullable=False)
    contribution: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    observation: Mapped[HistoricalObservationModel] = relationship(
        back_populates="evidence_snapshots"
    )
