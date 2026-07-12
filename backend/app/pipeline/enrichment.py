"""Derived metadata enrichment."""

from dataclasses import replace

from backend.app.domain.content import Content
from backend.app.pipeline.base import ContentStage


class ContentEnrichment(ContentStage):
    """Add deterministic metadata that does not depend on a platform SDK."""

    def process(self, content: Content) -> Content:
        """Add lightweight metadata about normalized content."""
        metadata = {
            **content.metadata,
            "description_length": len(content.description or ""),
            "title_length": len(content.title),
        }
        return replace(content, metadata=metadata)
