"""Content opportunity domain object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContentOpportunity:
    """A potential content opportunity identified by future workflows."""

    score: float
    competition: float
    growth_rate: float
    recommended_action: str
    estimated_rpm: float | None
    confidence: float
