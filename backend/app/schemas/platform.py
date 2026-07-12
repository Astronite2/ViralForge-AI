"""Platform API schemas."""

from backend.app.schemas.base import Schema


class PlatformRead(Schema):
    id: int
    name: str
