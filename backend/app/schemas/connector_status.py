"""Connector runtime status API schemas."""

from datetime import datetime

from backend.app.schemas.base import Schema


class ConnectorStatusRead(Schema):
    """Read-only state for one configured connector."""

    connector_name: str
    status: str
    enabled: bool
    provider: str | None
    provider_experimental: bool
    last_run_at: datetime | None
    last_success_at: datetime | None
    error_code: str | None
    message: str | None
