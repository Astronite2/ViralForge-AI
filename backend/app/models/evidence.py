"""Decision evidence persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.decision import DecisionModel
    from backend.app.models.trend_signal import TrendSignalModel


class EvidenceModel(TimestampMixin, Base):
    """Persisted scoring evidence for one decision factor."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    signal_id: Mapped[str] = mapped_column(
        ForeignKey("trend_signals.id"), nullable=False, index=True
    )
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("decisions.id"), nullable=False, index=True
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
    correlation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)

    signal: Mapped[TrendSignalModel] = relationship(back_populates="evidence")
    decision: Mapped[DecisionModel] = relationship(back_populates="evidence")
