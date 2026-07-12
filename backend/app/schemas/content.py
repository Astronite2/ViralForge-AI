"""Normalized content API schemas."""

from datetime import datetime
from typing import Any

from backend.app.schemas.base import Schema


class ContentRead(Schema):
    """Read representation of normalized content."""

    id: str
    platform: str
    creator_name: str
    creator_id: str
    title: str
    description: str | None
    url: str
    language: str | None
    country: str | None
    published_at: datetime
    duration_seconds: int | None
    content_type: str
    metrics: dict[str, float]
    analysis: dict[str, Any]
    metadata: dict[str, Any]
