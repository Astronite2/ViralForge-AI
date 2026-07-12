"""Trend signal domain object."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class TrendSignal:
    """A platform-neutral indicator of content momentum."""

    source: str
    score: float
    confidence: float
    timestamp: datetime
    reason: str
