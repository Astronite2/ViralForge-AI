"""Decision calculated domain event."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from backend.app.core.config import settings


@dataclass(frozen=True, slots=True)
class DecisionCalculated:
    """Immutable event emitted after a decision is committed."""

    event_id: str = field(default_factory=lambda: str(uuid4()))
    decision_id: str = ""
    topic_id: str = ""
    topic_name: str = ""
    score: float = 0.0
    confidence: float = 0.0
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = ""
    engine_version: str = ""
    event_version: str = field(default_factory=lambda: settings.event_version)
