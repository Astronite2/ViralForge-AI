"""Channel API schemas."""

from backend.app.schemas.base import Schema


class ChannelRead(Schema):
    id: int
    platform_id: int
    external_id: str
    name: str
