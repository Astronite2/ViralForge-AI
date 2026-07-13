"""Connector runtime status routes."""

from fastapi import APIRouter

from backend.app.schemas.connector_status import ConnectorStatusRead
from backend.app.services.connector_status import ConnectorStatusStore

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors-v1"])


@router.get("/status", response_model=list[ConnectorStatusRead])
def list_connector_statuses() -> list[ConnectorStatusRead]:
    """Return current configured connector states, independent of old signals."""
    return [
        ConnectorStatusRead.model_validate(status)
        for status in ConnectorStatusStore().list_statuses()
    ]
