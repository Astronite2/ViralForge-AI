"""Trend signal read endpoints."""

from fastapi import APIRouter

from backend.app.schemas.trend_signal import TrendSignalRead
from backend.app.services.trend import TrendService

router = APIRouter(prefix="/signals", tags=["signals"])
service = TrendService()


@router.get("", response_model=list[TrendSignalRead])
def list_signals() -> list[TrendSignalRead]:
    """Return trend signal placeholders."""
    return service.list_signals()
