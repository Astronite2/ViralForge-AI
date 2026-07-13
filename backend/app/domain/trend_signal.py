"""Trend signal domain object."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TrendSignal:
    """A platform-neutral indicator of content momentum."""

    source: str
    score: float
    confidence: float
    timestamp: datetime
    reason: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
