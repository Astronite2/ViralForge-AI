"""Health API schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness endpoint response."""

    status: str


class ReadyResponse(BaseModel):
    """Readiness endpoint response."""

    status: str
    postgres: str
    redis: str
