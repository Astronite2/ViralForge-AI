"""Topic persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.decision import DecisionModel
    from backend.app.models.trend_signal import TrendSignalModel


class Topic(TimestampMixin, Base):
    """Normalized topic record used by the intelligence flow."""

    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_key: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, unique=True
    )

    signals: Mapped[list[TrendSignalModel]] = relationship(
        back_populates="topic", cascade="all,delete-orphan"
    )
    decisions: Mapped[list[DecisionModel]] = relationship(back_populates="topic")
