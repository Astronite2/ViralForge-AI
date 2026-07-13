"""AI reasoning domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ReasoningType(StrEnum):
    """Supported reasoning modes."""

    DECISION_EXPLANATION = "decision_explanation"
    OPPORTUNITY_COMPARISON = "opportunity_comparison"
    EXECUTION_STRATEGY = "execution_strategy"
    CHANGE_SUMMARY = "change_summary"


class ReasoningStatus(StrEnum):
    """Persisted reasoning run status values."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    DISABLED = "DISABLED"


@dataclass(frozen=True, slots=True)
class ReasoningMessage:
    """A single prompt message passed to the provider."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ReasoningEvidenceReference:
    """Grounded evidence cited by a reasoning output."""

    evidence_id: str
    source: str
    factor: str
    claim: str
    contribution: float
    confidence: float


@dataclass(frozen=True, slots=True)
class ReasoningAlternativeTopicComparison:
    """A deterministic topic comparison used by the reasoning layer."""

    topic_id: str
    topic_name: str
    opportunity_score: float
    decision_score: float
    relative_strengths: tuple[str, ...] = ()
    relative_weaknesses: tuple[str, ...] = ()
    comparison_summary: str = ""


@dataclass(frozen=True, slots=True)
class ReasoningPromptBundle:
    """Versioned prompt messages for provider execution."""

    prompt_version: str
    messages: tuple[ReasoningMessage, ...]


@dataclass(frozen=True, slots=True)
class ReasoningRequest:
    """A reasoning request with all execution metadata."""

    reasoning_type: ReasoningType
    prompt_version: str
    context_version: str
    model_provider: str
    model_name: str
    messages: tuple[ReasoningMessage, ...]
    correlation_id: str
    decision_id: str | None = None
    topic_id: str | None = None
    opportunity_id: str | None = None
    topic_ids: tuple[str, ...] = ()
    opportunity_ids: tuple[str, ...] = ()
    previous_decision_id: str | None = None
    current_decision_id: str | None = None
    target_platform: str | None = None
    force_refresh: bool = False
    max_output_tokens: int = 0
    max_context_tokens: int = 0
    temperature: float = 0.0


@dataclass(frozen=True, slots=True)
class ReasoningContext:
    """Deterministic context assembled from persisted intelligence data."""

    context_version: str
    reasoning_type: ReasoningType
    topic: dict[str, object]
    facts: dict[str, object]
    scores: dict[str, object]
    evidence: tuple[ReasoningEvidenceReference, ...]
    uncertainty: dict[str, object]
    missing_data: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    traceability: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReasoningProviderResponse:
    """Raw structured output returned by a provider."""

    provider: str
    model: str
    raw_json: dict[str, object]
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None


@dataclass(frozen=True, slots=True)
class ReasoningValidationIssue:
    """A grounding or structural validation failure."""

    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ReasoningRun:
    """Persisted reasoning execution metadata."""

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


@dataclass(frozen=True, slots=True)
class ReasoningResult:
    """Grounded reasoning output persisted for read APIs."""

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
    supporting_evidence: tuple[ReasoningEvidenceReference, ...]
    conflicting_evidence: tuple[ReasoningEvidenceReference, ...]
    caveats: tuple[str, ...]
    confidence_assessment: str
    recommended_execution: dict[str, object]
    alternative_topics: tuple[ReasoningAlternativeTopicComparison, ...]
    source_references: tuple[ReasoningEvidenceReference, ...]
    model_provider: str
    model_name: str
    prompt_version: str
    context_version: str
    input_hash: str
    created_at: datetime
    completed_at: datetime | None
    correlation_id: str
    raw_output: dict[str, object]
