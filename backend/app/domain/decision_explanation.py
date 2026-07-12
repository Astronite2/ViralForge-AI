"""Decision explanation domain model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    """Human-readable explanation for an individual scoring factor."""

    factor: str
    weight: float
    contribution: float
    confidence: float
    reason: str
