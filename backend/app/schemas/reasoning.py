"""AI reasoning API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.app.domain.reasoning import ReasoningStatus, ReasoningType
from backend.app.schemas.base import Schema


class ReasoningEvidenceReferenceRead(Schema):
    """Serializable evidence reference used by reasoning output."""

    evidence_id: str
    source: str
    factor: str
    claim: str
    contribution: float
    confidence: float


class ReasoningAlternativeTopicComparisonRead(Schema):
    """Serializable alternative topic comparison."""

    topic_id: str
    topic_name: str
    opportunity_score: float
    decision_score: float
    relative_strengths: list[str]
    relative_weaknesses: list[str]
    comparison_summary: str


class ReasoningRunRead(Schema):
    """Serializable reasoning execution metadata."""

    id: str
    reasoning_type: ReasoningType
    status: ReasoningStatus
    topic_id: str | None
    decision_id: str | None
    opportunity_id: str | None
    provider: str
    model: str
    prompt_version: str
    context_version: str
    input_hash: str
    force_refresh: bool
    retry_count: int
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: float | None
    created_at: datetime
    completed_at: datetime | None
    correlation_id: str


class ReasoningResultRead(Schema):
    """Serializable grounded reasoning output."""

    id: str
    reasoning_run_id: str
    topic_id: str | None
    decision_id: str | None
    opportunity_id: str | None
    reasoning_type: ReasoningType
    status: ReasoningStatus
    executive_summary: str
    why_now: str
    why_this_topic: str
    why_this_platform: str
    what_changed: str
    supporting_evidence: list[ReasoningEvidenceReferenceRead]
    conflicting_evidence: list[ReasoningEvidenceReferenceRead]
    caveats: list[str]
    confidence_assessment: str
    recommended_execution: dict[str, object]
    alternative_topics: list[ReasoningAlternativeTopicComparisonRead]
    source_references: list[ReasoningEvidenceReferenceRead]
    model_provider: str
    model_name: str
    prompt_version: str
    context_version: str
    input_hash: str
    created_at: datetime
    completed_at: datetime | None
    correlation_id: str
    raw_output: dict[str, object]


class ReasoningDisabledRead(Schema):
    """Typed disabled or misconfigured response."""

    status: str
    provider: str | None = None
    model: str | None = None
    detail: str


class DecisionExplanationReasoningRequest(Schema):
    """Request a reasoning explanation for one decision."""

    decision_id: str
    force_refresh: bool = False


class OpportunityComparisonReasoningRequest(Schema):
    """Request a reasoning comparison across topics or opportunities."""

    topic_ids: list[str] | None = None
    opportunity_ids: list[str] | None = None
    force_refresh: bool = False


class ExecutionStrategyReasoningRequest(Schema):
    """Request an execution strategy for one decision."""

    decision_id: str
    target_platform: str | None = None
    force_refresh: bool = False


class ChangeSummaryReasoningRequest(Schema):
    """Request a reasoning summary of topic or decision changes."""

    topic_id: str
    previous_decision_id: str | None = None
    current_decision_id: str | None = None
    force_refresh: bool = False


class ReasoningValidationErrorRead(Schema):
    """Serializable grounding validation failure."""

    field: str
    message: str


class ReasoningRequestStatusRead(Schema):
    """Serializable reasoning run status response."""

    run: ReasoningRunRead
    result: ReasoningResultRead | None = None
    validation_errors: list[ReasoningValidationErrorRead] = Field(default_factory=list)
