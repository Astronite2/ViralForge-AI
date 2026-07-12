"""Processed event persistence access."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.processed_event import ProcessedEventModel
from backend.app.repositories.base import Repository


class ProcessedEventRepository(Repository):
    """Database access boundary for idempotency records."""

    def exists(self, event_id: str) -> bool:
        query = self.session.query(ProcessedEventModel).filter(
            ProcessedEventModel.event_id == event_id
        )
        return self.session.query(query.exists()).scalar() is True

    def get_by_event_id(self, event_id: str) -> ProcessedEventModel | None:
        query = self.session.query(ProcessedEventModel).filter(
            ProcessedEventModel.event_id == event_id
        )
        return query.one_or_none()

    def create_processed_record(
        self,
        *,
        event_id: str,
        event_type: str,
        correlation_id: str,
        decision_id: str | None = None,
    ) -> ProcessedEventModel:
        model = ProcessedEventModel(
            event_id=event_id,
            event_type=event_type,
            processed_at=datetime.now(UTC),
            correlation_id=correlation_id,
            decision_id=decision_id,
        )
        self.session.add(model)
        self.session.flush()
        return model
