"""Decision Engine application service."""

from datetime import UTC, datetime

from backend.app.domain.content import Content
from backend.app.domain.decision import Decision
from backend.app.domain.trend_signal import TrendSignal
from backend.app.services.decision_engine import DecisionEngine


class DecisionService:
    """Provide deterministic decision use cases to the API layer."""

    def __init__(self, engine: DecisionEngine | None = None) -> None:
        self.engine = engine or DecisionEngine()

    def demo(self) -> Decision:
        """Return a traceable deterministic recommendation using placeholder input."""
        content = Content(
            id="demo-content",
            platform="demo",
            creator_name="Demo Creator",
            creator_id="demo-creator",
            title="Decision Engine Demo",
            description="Placeholder content for the decision endpoint.",
            url="https://example.com/demo-content",
            language="en",
            country="US",
            published_at=datetime(2026, 1, 1, tzinfo=UTC),
            duration_seconds=60,
            content_type="video",
            metadata={
                "topic_id": "demo-topic",
                "topic_name": "Decision Engine Demo",
                "signal_id": "demo-signal",
                "correlation_id": "demo-correlation",
                "event_version": "v1",
                "decision_factors": {
                    "audience_demand": 0.82,
                    "revenue_potential": 0.68,
                    "competition": 0.18,
                    "evergreen": 0.61,
                    "platform_fit": 0.88,
                    "confidence": 0.94,
                },
                "decision_confidence": {
                    "audience_demand": 0.91,
                    "revenue_potential": 0.78,
                    "competition": 0.88,
                    "evergreen": 0.76,
                    "platform_fit": 0.93,
                    "confidence": 0.94,
                },
                "decision_reasons": {
                    "trend_momentum": "Google Trends growth is accelerating.",
                    "competition": "Competition is below average.",
                },
            },
        )
        signals = (
            TrendSignal(
                source="demo_signal",
                score=0.94,
                confidence=0.94,
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                reason="Demo signal.",
            ),
        )
        return self.engine.evaluate(content, signals)
