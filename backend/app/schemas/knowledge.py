"""Knowledge-layer API schemas."""

from __future__ import annotations

from datetime import datetime

from backend.app.domain.knowledge import TopicRelationshipType
from backend.app.schemas.base import Schema


class HistoricalObservationRead(Schema):
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


class HistoricalEvidenceRead(Schema):
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


class HistoricalAnalyticsRead(Schema):
    growth_rate: float
    acceleration: float
    momentum: float
    peak_detected: bool
    decline_detected: bool
    freshness: float
    trend_age: float
    historical_volatility: float
    connector_contributions: dict[str, float]
    timeline: list[dict[str, object]]


class OpportunityScoreRead(Schema):
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


class TopicHistoryRead(Schema):
    topic_id: str
    topic_name: str
    observations: list[HistoricalObservationRead]
    analytics: HistoricalAnalyticsRead
    evidence_history: list[HistoricalEvidenceRead]
    opportunity_scores: list[OpportunityScoreRead]


class TopicGraphRelationshipRead(Schema):
    id: str
    source_topic_id: str
    target_topic_id: str
    relationship_type: TopicRelationshipType
    strength: float
    reason: str
    correlation_id: str
    created_at: datetime


class TopicGraphRead(Schema):
    topic_id: str
    topic_name: str
    relationships: list[TopicGraphRelationshipRead]
