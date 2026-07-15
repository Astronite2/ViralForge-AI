"""Persistent source-grounded documentary script."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin


class ProjectScriptModel(TimestampMixin, Base):
    __tablename__ = "project_scripts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[str] = mapped_column(String(32))
    research_version_used: Mapped[str | None] = mapped_column(String(32), nullable=True)
    production_brief_version_used: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    current_step: Mapped[str] = mapped_column(String(40))
    target_word_count: Mapped[int] = mapped_column(Integer, default=0)
    actual_word_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_duration_minutes: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    evidence_sufficiency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    safe_error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
