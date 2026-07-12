"""Metric persistence model."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin


class Metric(TimestampMixin, Base):
    """Placeholder content metric record."""

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float]
