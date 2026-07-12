"""Validation for connector payloads."""

from collections.abc import Mapping
from typing import Any

from backend.app.pipeline.base import RawContentValidator


class ContentValidator(RawContentValidator):
    """Validate the platform-neutral raw content contract."""

    required_fields = frozenset(
        {
            "id",
            "platform",
            "creator_name",
            "creator_id",
            "title",
            "url",
            "published_at",
            "content_type",
        }
    )

    def validate(self, raw_content: Mapping[str, Any]) -> None:
        """Raise ValueError when required content values are absent."""
        missing = sorted(
            field for field in self.required_fields if not raw_content.get(field)
        )
        if missing:
            message = ", ".join(missing)
            raise ValueError(f"Missing required content fields: {message}")
