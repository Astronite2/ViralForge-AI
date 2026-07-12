"""Decision engine enumerations."""

from enum import StrEnum


class DecisionType(StrEnum):
    """Actions produced by the deterministic decision engine."""

    CREATE = "create"
    WAIT = "wait"
    IGNORE = "ignore"
    REVIEW = "review"


class SignalStrength(StrEnum):
    """Human-readable bands for normalized signal scores."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
