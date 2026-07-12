"""Trend signal persistence access."""

from datetime import UTC, datetime

from backend.app.domain.trend_signal import TrendSignal
from backend.app.models.trend_signal import TrendSignalModel
from backend.app.repositories.base import Repository


class TrendRepository(Repository):
    """Database access boundary for trend signals."""

    def create(self, content_id: str, signal: TrendSignal) -> TrendSignalModel:
        """Store a content trend signal without committing the session."""
        model = TrendSignalModel(
            topic_id=None,
            content_id=content_id,
            source=signal.source,
            score=signal.score,
            confidence=signal.confidence,
            timestamp=signal.timestamp,
            reason=signal.reason,
            correlation_id=content_id,
            raw_metadata={
                "content_id": content_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        self.session.add(model)
        self.session.flush()
        return model

    def list(self) -> list[TrendSignalModel]:
        """Return all stored trend signals."""
        query = self.session.query(TrendSignalModel).order_by(
            TrendSignalModel.timestamp
        )
        return list(query)
