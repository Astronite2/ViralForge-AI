"""Decision persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.decision_explanation import DecisionExplanationModel
    from backend.app.models.evidence import EvidenceModel
    from backend.app.models.topic import Topic


class DecisionModel(TimestampMixin, Base):
    """Immutable deterministic decision record."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id"), nullable=False, index=True
    )
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(255), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    event_version: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    weights_snapshot: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
        server_default=func.now(),
    )
    topic: Mapped[Topic] = relationship(back_populates="decisions")
    evidence: Mapped[list[EvidenceModel]] = relationship(back_populates="decision")
    explanations: Mapped[list[DecisionExplanationModel]] = relationship(
        back_populates="decision", cascade="all,delete-orphan"
    )
