"""Trend signal API schemas."""

from datetime import datetime

from backend.app.schemas.base import Schema


class TrendSignalRead(Schema):
    """Read representation of a trend signal."""

    id: str
    topic_id: str | None
    topic_name: str
    source: str
    score: float
    confidence: float
    reason: str
    timestamp: datetime
    correlation_id: str
    created_at: datetime
    raw_metadata: dict[str, object] | None = None
