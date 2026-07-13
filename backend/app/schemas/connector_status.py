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


class ConnectorRead(Schema):
    name: str
    display_name: str
    version: str
    provider: str
    provider_experimental: bool
    description: str
    enabled: bool
    supports_live_access: bool
    supports_fixture_access: bool
    capabilities: list[str]
    runtime_status: ConnectorStatusRead


class ConnectorCapabilityRead(Schema):
    value: str
    description: str
