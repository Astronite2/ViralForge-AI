"""Persistence models for the YouTube money-opportunity validation loop."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin


class MoneyAnalysisModel(TimestampMixin, Base):
    __tablename__ = "money_opportunity_analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    query: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    channel_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class MoneyOpportunityModel(TimestampMixin, Base):
    __tablename__ = "money_opportunity_recommendations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("money_opportunity_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rank: Mapped[int] = mapped_column(nullable=False)
    topic: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    money_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ProductionBriefModel(TimestampMixin, Base):
    __tablename__ = "money_production_briefs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    opportunity_id: Mapped[str] = mapped_column(
        ForeignKey("money_opportunity_recommendations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class MoneyOutcomeModel(TimestampMixin, Base):
    __tablename__ = "money_opportunity_outcomes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("money_opportunity_recommendations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    selected_topic: Mapped[str] = mapped_column(String(300), nullable=False)
    money_score_at_selection: Mapped[float] = mapped_column(Float, nullable=False)
    publish_status: Mapped[str] = mapped_column(String(32), nullable=False)
    youtube_video_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    production_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    views_after_24_hours: Mapped[int | None] = mapped_column(nullable=True)
    views_after_7_days: Mapped[int | None] = mapped_column(nullable=True)
    views_after_30_days: Mapped[int | None] = mapped_column(nullable=True)
    watch_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    subscribers_gained: Mapped[int | None] = mapped_column(nullable=True)
    rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_notes: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    result_classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )
