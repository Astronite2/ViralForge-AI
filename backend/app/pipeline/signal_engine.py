"""Platform-neutral trend signal creation."""

from dataclasses import replace
from datetime import UTC, datetime

from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.pipeline.base import ContentStage


class SignalEngine(ContentStage):
    """Create a baseline signal for a successfully normalized item."""

    def process(self, content: Content) -> Content:
        """Attach a placeholder ingestion signal to content."""
        signal = TrendSignal(
            source="content_pipeline",
            score=0.0,
            confidence=0.0,
            timestamp=datetime.now(UTC),
            reason="Signal scoring is not configured.",
        )
        return replace(content, signals=(*content.signals, signal))
