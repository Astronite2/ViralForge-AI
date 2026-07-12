"""Decision explanation persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.decision import DecisionModel


class DecisionExplanationModel(TimestampMixin, Base):
    """Persisted explanation for one decision factor."""

    __tablename__ = "decision_explanations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("decisions.id"), nullable=False, index=True
    )
    factor: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    contribution: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)

    decision: Mapped[DecisionModel] = relationship(back_populates="explanations")
