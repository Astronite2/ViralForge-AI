"""Conversion from connector payloads to normalized content."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from backend.app.domain.content import Content


class ContentNormalizer:
    """Build a platform-independent Content object from connector payloads."""

    def normalize(self, raw_content: Mapping[str, Any]) -> Content:
        """Normalize raw connector data after validation."""
        return Content(
            id=str(raw_content["id"]),
            platform=str(raw_content["platform"]),
            creator_name=str(raw_content["creator_name"]),
            creator_id=str(raw_content["creator_id"]),
            title=str(raw_content["title"]),
            description=self._optional_string(raw_content.get("description")),
            url=str(raw_content["url"]),
            language=self._optional_string(raw_content.get("language")),
            country=self._optional_string(raw_content.get("country")),
            published_at=self._as_datetime(raw_content["published_at"]),
            duration_seconds=self._optional_int(raw_content.get("duration_seconds")),
            content_type=str(raw_content["content_type"]),
            metrics=self._float_mapping(raw_content.get("metrics")),
            analysis=self._mapping(raw_content.get("analysis")),
            metadata=self._mapping(raw_content.get("metadata")),
        )

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise ValueError("published_at must be an ISO 8601 timestamp or datetime")

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return int(value) if value is not None else None

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ValueError("Expected a mapping")
        return {str(key): item for key, item in value.items()}

    @classmethod
    def _float_mapping(cls, value: Any) -> dict[str, float]:
        return {key: float(item) for key, item in cls._mapping(value).items()}
