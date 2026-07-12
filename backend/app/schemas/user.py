"""User API schemas."""

from backend.app.schemas.base import Schema


class UserRead(Schema):
    id: int
    email: str
