"""Normalized content persistence access."""

from backend.app.domain.content import Content
from backend.app.models.content import ContentModel
from backend.app.repositories.base import Repository


class ContentRepository(Repository):
    """Database access boundary for normalized content."""

    def get(self, content_id: str) -> ContentModel | None:
        """Return one content record by its platform-independent identifier."""
        return self.session.get(ContentModel, content_id)

    def list(self) -> list[ContentModel]:
        """Return all normalized content records."""
        query = self.session.query(ContentModel).order_by(ContentModel.published_at)
        return list(query)

    def save(self, content: Content) -> ContentModel:
        """Insert or update normalized content without committing the session.

        The connector-provided content identifier is the idempotency key. Keeping
        the flush inside this repository guarantees that dependent rows can safely
        reference the content within the caller's transaction.
        """
        model = self.get(content.id)
        values = {
            "platform": content.platform,
            "creator_name": content.creator_name,
            "creator_id": content.creator_id,
            "title": content.title,
            "description": content.description,
            "url": content.url,
            "language": content.language,
            "country": content.country,
            "published_at": content.published_at,
            "duration_seconds": content.duration_seconds,
            "content_type": content.content_type,
            "metrics": dict(content.metrics),
            "analysis": dict(content.analysis),
            "metadata_": dict(content.metadata),
        }
        if model is None:
            model = ContentModel(id=content.id, **values)
            self.session.add(model)
        else:
            for field, value in values.items():
                setattr(model, field, value)
        self.session.flush()
        return model

    def upsert(self, content: Content) -> ContentModel:
        """Backward-compatible alias for :meth:`save`."""
        return self.save(content)
