"""Topic graph relationship persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.topic import Topic


class TopicRelationshipModel(TimestampMixin, Base):
    """Persisted directed relationship between two topics."""

    __tablename__ = "topic_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_topic_id",
            "target_topic_id",
            "relationship_type",
            name="uq_topic_relationships_edge",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    source_topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id"), nullable=False, index=True
    )
    target_topic_id: Mapped[str] = mapped_column(
        ForeignKey("topics.id"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    source_topic: Mapped[Topic] = relationship("Topic", foreign_keys=[source_topic_id])
    target_topic: Mapped[Topic] = relationship("Topic", foreign_keys=[target_topic_id])
