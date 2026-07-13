"""Opportunity score API schemas."""

from datetime import datetime

from backend.app.schemas.base import Schema


class OpportunityRead(Schema):
    """Serializable opportunity score history entry."""

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
