"""Platform-independent normalized content domain model."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.app.domain.trend_signal import TrendSignal


@dataclass(frozen=True, slots=True)
class Content:
    """Normalized content collected from any supported platform."""

    id: str
    platform: str
    creator_name: str
    creator_id: str
    title: str
    description: str | None
    url: str
    language: str | None
    country: str | None
    published_at: datetime
    duration_seconds: int | None
    content_type: str
    metrics: Mapping[str, float] = field(default_factory=dict)
    analysis: Mapping[str, Any] = field(default_factory=dict)
    signals: tuple[TrendSignal, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
