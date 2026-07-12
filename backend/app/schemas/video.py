"""Video API schemas."""

from backend.app.schemas.base import Schema


class VideoRead(Schema):
    id: int
    channel_id: int
    external_id: str
    title: str
