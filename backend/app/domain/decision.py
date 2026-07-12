"""Explainable deterministic decision domain model."""

from dataclasses import dataclass
from datetime import datetime

from backend.app.domain.decision_enums import DecisionType
from backend.app.domain.decision_explanation import DecisionExplanation
from backend.app.domain.evidence import Evidence


@dataclass(frozen=True, slots=True)
class Decision:
    """A complete, traceable recommendation produced by the decision engine."""

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
    evidence: tuple[Evidence, ...]
    explanations: tuple[DecisionExplanation, ...]
