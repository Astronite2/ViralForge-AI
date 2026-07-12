"""Normalized content query service."""

from datetime import UTC, datetime

from backend.app.schemas.content import ContentRead


class ContentService:
    """Application service for placeholder content read operations."""

    def list_content(self) -> list[ContentRead]:
        """Return placeholder content until query persistence is enabled."""
        return []

    def get_content(self, content_id: str) -> ContentRead:
        """Return a placeholder normalized item for the requested identifier."""
        return ContentRead(
            id=content_id,
            platform="placeholder",
            creator_name="Placeholder Creator",
            creator_id="placeholder-creator",
            title="Placeholder Content",
            description=None,
            url="https://example.com/content",
            language=None,
            country=None,
            published_at=datetime.now(UTC),
            duration_seconds=None,
            content_type="placeholder",
            metrics={},
            analysis={"status": "pending"},
            metadata={},
        )


class VideoService:
    """Placeholder application service retained for video workflows."""
