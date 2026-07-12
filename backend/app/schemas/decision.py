"""Decision Engine API schemas."""

from datetime import datetime

from backend.app.domain.decision_enums import DecisionType
from backend.app.schemas.base import Schema


class EvidenceRead(Schema):
    """Serializable factor evidence."""

    id: str
    source: str
    factor: str
    raw_value: float
    normalized_value: float
    weight: float
    contribution: float
    confidence: float
    reason: str
    timestamp: datetime
    signal_id: str


class DecisionExplanationRead(Schema):
    """Serializable decision factor explanation."""

    factor: str
    weight: float
    contribution: float
    confidence: float
    reason: str


class DecisionRead(Schema):
    """Serializable complete deterministic recommendation."""

    id: str
    topic_id: str
    topic_name: str
    decision_type: DecisionType
    score: float
    confidence: float
    summary: str
    recommended_action: str
    created_at: datetime
    engine_version: str
    event_version: str
    correlation_id: str
    weights_snapshot: dict[str, float]
    evidence: list[EvidenceRead]
    explanations: list[DecisionExplanationRead]
