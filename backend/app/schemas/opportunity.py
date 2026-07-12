"""Opportunity API schemas."""

from backend.app.schemas.base import Schema


class OpportunityRead(Schema):
    score: float
    competition: float
    growth_rate: float
    recommended_action: str
    estimated_rpm: float | None
    confidence: float
