"""Platform connector SDK."""

from backend.app.connectors.base import BaseConnector
from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.connectors.registry import (
    ConnectorRegistry,
    build_default_connector_registry,
)

__all__ = [
    "BaseConnector",
    "ConnectorRegistry",
    "GoogleTrendsConnector",
    "build_default_connector_registry",
]
