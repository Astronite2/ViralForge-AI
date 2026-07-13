"""Knowledge-layer domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TopicRelationshipType(StrEnum):
    """Supported topic graph relationship types."""

    RELATED = "related"
    BROADER = "broader"
    NARROWER = "narrower"
    ALTERNATIVE = "alternative"


@dataclass(frozen=True, slots=True)
class HistoricalObservation:
    """An immutable historical observation for a topic."""

    id: str
    topic_id: str
    source: str
    connector_name: str
    observation_type: str
    observed_at: datetime
    correlation_id: str
    observation_hash: str
    payload: dict[str, object]
    change_type: str
    signal_id: str | None = None
    content_id: str | None = None
    previous_observation_id: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalEvidenceSnapshot:
    """A historical copy of decision evidence."""

    id: str
    topic_id: str
    observation_id: str
    evidence_id: str
    signal_id: str
    source: str
    factor: str
    weight: float
    raw_value: float
    normalized_value: float
    contribution: float
    confidence: float
    reason: str
    timestamp: datetime
    correlation_id: str


@dataclass(frozen=True, slots=True)
class HistoricalAnalytics:
    """Deterministic analytics derived from topic history."""

    growth_rate: float
    acceleration: float
    momentum: float
    peak_detected: bool
    decline_detected: bool
    freshness: float
    trend_age: float
    historical_volatility: float
    connector_contributions: dict[str, float] = field(default_factory=dict)
    timeline: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class OpportunityScore:
    """A persisted opportunity score with explainable factors."""

    id: str
    topic_id: str
    observation_id: str | None
    score: float
    confidence: float
    version: str
    dimensions: dict[str, float]
    explanations: dict[str, str]
    correlation_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TopicRelationship:
    """A directed relationship between two normalized topics."""

    id: str
    source_topic_id: str
    target_topic_id: str
    relationship_type: TopicRelationshipType
    strength: float
    reason: str
    correlation_id: str
    created_at: datetime
