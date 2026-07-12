"""Topic API schemas."""

from datetime import datetime

from backend.app.schemas.base import Schema


class TopicRead(Schema):
    """Read representation of a normalized topic."""

    id: str
    display_name: str
    normalized_key: str
    created_at: datetime
