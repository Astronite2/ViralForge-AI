"""AI reasoning persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.base import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.decision import DecisionModel
    from backend.app.models.opportunity_score import OpportunityScoreModel
    from backend.app.models.topic import Topic


def _json_type() -> object:
    return JSON().with_variant(JSONB(), "postgresql")


class ReasoningRunModel(TimestampMixin, Base):
    """Persisted reasoning run metadata."""

    __tablename__ = "reasoning_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    reasoning_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    topic_id: Mapped[str | None] = mapped_column(
        ForeignKey("topics.id"), nullable=True, index=True
    )
    decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("decisions.id"), nullable=True, index=True
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_scores.id"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    context_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    force_refresh: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    topic: Mapped[Topic | None] = relationship("Topic")
    decision: Mapped[DecisionModel | None] = relationship("DecisionModel")
    opportunity: Mapped[OpportunityScoreModel | None] = relationship(
        "OpportunityScoreModel"
    )
    result: Mapped[ReasoningResultModel | None] = relationship(
        back_populates="run", uselist=False
    )
    validation_errors: Mapped[list[ReasoningValidationErrorModel]] = relationship(
        back_populates="run", cascade="all,delete-orphan"
    )


class ReasoningResultModel(TimestampMixin, Base):
    """Persisted structured reasoning output."""

    __tablename__ = "reasoning_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    reasoning_run_id: Mapped[str] = mapped_column(
        ForeignKey("reasoning_runs.id"), nullable=False, unique=True, index=True
    )
    reasoning_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    topic_id: Mapped[str | None] = mapped_column(
        ForeignKey("topics.id"), nullable=True, index=True
    )
    decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("decisions.id"), nullable=True, index=True
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_scores.id"), nullable=True, index=True
    )
    executive_summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    why_now: Mapped[str] = mapped_column(String(2000), nullable=False)
    why_this_topic: Mapped[str] = mapped_column(String(2000), nullable=False)
    why_this_platform: Mapped[str] = mapped_column(String(2000), nullable=False)
    what_changed: Mapped[str] = mapped_column(String(2000), nullable=False)
    supporting_evidence: Mapped[list[dict[str, object]]] = mapped_column(
        _json_type(), nullable=False
    )
    conflicting_evidence: Mapped[list[dict[str, object]]] = mapped_column(
        _json_type(), nullable=False
    )
    caveats: Mapped[list[str]] = mapped_column(_json_type(), nullable=False)
    confidence_assessment: Mapped[str] = mapped_column(String(2000), nullable=False)
    recommended_execution: Mapped[dict[str, object]] = mapped_column(
        _json_type(), nullable=False
    )
    alternative_topics: Mapped[list[dict[str, object]]] = mapped_column(
        _json_type(), nullable=False
    )
    source_references: Mapped[list[dict[str, object]]] = mapped_column(
        _json_type(), nullable=False
    )
    model_provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    context_version: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    raw_output: Mapped[dict[str, object]] = mapped_column(_json_type(), nullable=False)

    run: Mapped[ReasoningRunModel] = relationship(back_populates="result")
    source_links: Mapped[list[ReasoningSourceLinkModel]] = relationship(
        back_populates="result", cascade="all,delete-orphan"
    )


class ReasoningSourceLinkModel(TimestampMixin, Base):
    """Traceability link between reasoning and grounded source records."""

    __tablename__ = "reasoning_source_links"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    reasoning_result_id: Mapped[str] = mapped_column(
        ForeignKey("reasoning_results.id"), nullable=False, index=True
    )
    link_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence.id"), nullable=True, index=True
    )
    topic_id: Mapped[str | None] = mapped_column(
        ForeignKey("topics.id"), nullable=True, index=True
    )
    decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("decisions.id"), nullable=True, index=True
    )
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunity_scores.id"), nullable=True, index=True
    )
    claim: Mapped[str] = mapped_column(String(2000), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    result: Mapped[ReasoningResultModel] = relationship(back_populates="source_links")


class ReasoningValidationErrorModel(TimestampMixin, Base):
    """Persisted validation error for a reasoning run."""

    __tablename__ = "reasoning_validation_errors"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    reasoning_run_id: Mapped[str] = mapped_column(
        ForeignKey("reasoning_runs.id"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    run: Mapped[ReasoningRunModel] = relationship(back_populates="validation_errors")
