"""Topic persistence access."""

from __future__ import annotations

from backend.app.models.topic import Topic
from backend.app.repositories.base import Repository


class TopicRepository(Repository):
    """Database access boundary for topics."""

    def get_by_id(self, topic_id: str) -> Topic | None:
        return self.session.get(Topic, topic_id)

    def get_by_normalized_key(self, normalized_key: str) -> Topic | None:
        query = self.session.query(Topic).filter(Topic.normalized_key == normalized_key)
        return query.one_or_none()

    def create(self, display_name: str, normalized_key: str) -> Topic:
        model = Topic(display_name=display_name, normalized_key=normalized_key)
        self.session.add(model)
        self.session.flush()
        return model

    def get_or_create(self, display_name: str, normalized_key: str) -> Topic:
        model = self.get_by_normalized_key(normalized_key)
        if model is not None:
            return model
        return self.create(display_name, normalized_key)

    def list(self, limit: int, offset: int) -> list[Topic]:
        query = (
            self.session.query(Topic)
            .order_by(Topic.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(query)
