"""Content opportunity persistence model."""

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin


class OpportunityModel(TimestampMixin, Base):
    """Persisted content opportunity score."""

    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[str] = mapped_column(ForeignKey("content.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    competition: Mapped[float] = mapped_column(Float)
    growth_rate: Mapped[float] = mapped_column(Float)
    recommended_action: Mapped[str] = mapped_column(String(255))
    estimated_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)


Opportunity = OpportunityModel
