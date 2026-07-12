"""Versioned trend signal routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.schemas.trend_signal import TrendSignalRead
from backend.app.services.intelligence_reads import IntelligenceReadService

router = APIRouter(prefix="/api/v1/signals", tags=["signals-v1"])


def _service(db: Session) -> IntelligenceReadService:
    return IntelligenceReadService(db)


@router.get("", response_model=list[TrendSignalRead])
def list_signals(
    limit: int = Query(default=settings.pagination_default_limit, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TrendSignalRead]:
    return _service(db).list_signals(min(limit, settings.pagination_max_limit), offset)


@router.get("/{signal_id}", response_model=TrendSignalRead)
def get_signal(signal_id: str, db: Session = Depends(get_db)) -> TrendSignalRead:
    signal = _service(db).get_signal(signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
