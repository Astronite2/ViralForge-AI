"""Traceable scoring evidence domain model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Evidence:
    """The raw and normalized inputs behind one decision factor."""

    id: str
    source: str
    factor: str
    weight: float
    raw_value: float
    normalized_value: float
    contribution: float
    confidence: float
    reason: str
    timestamp: datetime
    signal_id: str
    correlation_id: str
