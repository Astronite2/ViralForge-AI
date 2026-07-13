"""Opportunity score persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.historical_observation import HistoricalObservationModel
    from backend.app.models.topic import Topic


class OpportunityScoreModel(TimestampMixin, Base):
    """Persisted opportunity score history."""

    __tablename__ = "opportunity_scores"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id"), nullable=False, index=True
    )
    observation_id: Mapped[str | None] = mapped_column(
        ForeignKey("historical_observations.id"), nullable=True, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    dimensions: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    explanations: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    topic: Mapped[Topic] = relationship("Topic")
    observation: Mapped[HistoricalObservationModel | None] = relationship(
        "HistoricalObservationModel"
    )
