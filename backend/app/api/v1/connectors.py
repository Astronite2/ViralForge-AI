"""Connector runtime status routes."""

from fastapi import APIRouter, Query

from backend.app.connectors.metadata import (
    CAPABILITY_DESCRIPTIONS,
    ConnectorCapability,
)
from backend.app.connectors.registry import build_default_connector_registry
from backend.app.schemas.connector_status import (
    ConnectorCapabilityRead,
    ConnectorRead,
    ConnectorStatusRead,
)
from backend.app.services.connector_status import ConnectorStatusStore

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors-v1"])


def _registry():
    return build_default_connector_registry(include_disabled=True)


@router.get("/capabilities", response_model=list[ConnectorCapabilityRead])
def list_connector_capabilities() -> list[ConnectorCapabilityRead]:
    """Return the stable platform capability catalog."""
    return [
        ConnectorCapabilityRead(
            value=capability.value,
            description=CAPABILITY_DESCRIPTIONS[capability],
        )
        for capability in ConnectorCapability
    ]


@router.get("/status", response_model=list[ConnectorStatusRead])
def list_connector_statuses() -> list[ConnectorStatusRead]:
    """Return current configured connector states, independent of old signals."""
    return [
        ConnectorStatusRead.model_validate(status)
        for status in ConnectorStatusStore().list_statuses()
    ]


@router.get("", response_model=list[ConnectorRead])
def list_connectors(
    capability: ConnectorCapability | None = Query(default=None),
) -> list[ConnectorRead]:
    """Discover configured connectors and their current runtime states."""
    registry = _registry()
    metadata = registry.list_metadata()
    if capability is not None:
        allowed = {
            item.metadata.name for item in registry.filter_by_capability(capability)
        }
        metadata = tuple(item for item in metadata if item.name in allowed)
    statuses = {
        item.connector_name: ConnectorStatusRead.model_validate(item)
        for item in ConnectorStatusStore().list_statuses(metadata)
    }
    return [
        ConnectorRead(
            **item.model_dump(exclude={"capabilities"}),
            enabled=statuses[item.name].enabled,
            capabilities=list(item.capabilities.api_values()),
            runtime_status=statuses[item.name],
        )
        for item in metadata
    ]
