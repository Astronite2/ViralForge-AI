"""Historical observation persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.historical_evidence import HistoricalEvidenceModel
    from backend.app.models.opportunity_score import OpportunityScoreModel
    from backend.app.models.topic import Topic
    from backend.app.models.trend_signal import TrendSignalModel


class HistoricalObservationModel(TimestampMixin, Base):
    """Persisted historical observation for a topic."""

    __tablename__ = "historical_observations"
    __table_args__ = (
        UniqueConstraint("observation_hash", name="uq_historical_observations_hash"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    connector_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    observation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    observation_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    signal_id: Mapped[str | None] = mapped_column(
        ForeignKey("trend_signals.id"), nullable=True, index=True
    )
    content_id: Mapped[str | None] = mapped_column(
        ForeignKey("content.id"), nullable=True, index=True
    )
    previous_observation_id: Mapped[str | None] = mapped_column(
        ForeignKey("historical_observations.id"), nullable=True, index=True
    )

    topic: Mapped[Topic] = relationship("Topic")
    signal: Mapped[TrendSignalModel | None] = relationship("TrendSignalModel")
    evidence_snapshots: Mapped[list[HistoricalEvidenceModel]] = relationship(
        back_populates="observation", cascade="all,delete-orphan"
    )
    opportunity_scores: Mapped[list[OpportunityScoreModel]] = relationship(
        back_populates="observation"
    )
