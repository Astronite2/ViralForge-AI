"""Trend signal persistence access."""

from __future__ import annotations

from datetime import datetime

from backend.app.models.trend_signal import TrendSignalModel
from backend.app.repositories.base import Repository


class TrendSignalRepository(Repository):
    """Database access boundary for normalized trend signals."""

    def create(
        self,
        *,
        topic_id: str | None,
        source: str,
        score: float,
        confidence: float,
        timestamp: datetime,
        reason: str,
        correlation_id: str,
        raw_metadata: dict[str, object] | None = None,
        content_id: str | None = None,
    ) -> TrendSignalModel:
        model = TrendSignalModel(
            topic_id=topic_id,
            content_id=content_id,
            source=source,
            score=score,
            confidence=confidence,
            timestamp=timestamp,
            reason=reason,
            correlation_id=correlation_id,
            raw_metadata=raw_metadata or {},
        )
        self.session.add(model)
        self.session.flush()
        return model

    def get_by_id(self, signal_id: str) -> TrendSignalModel | None:
        return self.session.get(TrendSignalModel, signal_id)

    def list(self, limit: int, offset: int) -> list[TrendSignalModel]:
        query = (
            self.session.query(TrendSignalModel)
            .order_by(TrendSignalModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(query)

    def list_by_topic(
        self, topic_id: str, limit: int, offset: int
    ) -> list[TrendSignalModel]:
        query = (
            self.session.query(TrendSignalModel)
            .filter(TrendSignalModel.topic_id == topic_id)
            .order_by(TrendSignalModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(query)
