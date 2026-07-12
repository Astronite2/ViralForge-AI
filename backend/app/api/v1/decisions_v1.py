"""Versioned decision routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.schemas.decision import DecisionRead
from backend.app.services.intelligence_reads import IntelligenceReadService

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions-v1"])


def _service(db: Session) -> IntelligenceReadService:
    return IntelligenceReadService(db)


@router.get("", response_model=list[DecisionRead])
def list_decisions(
    limit: int = Query(default=settings.pagination_default_limit, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[DecisionRead]:
    return _service(db).list_decisions(
        min(limit, settings.pagination_max_limit), offset
    )


@router.get("/{decision_id}", response_model=DecisionRead)
def get_decision(decision_id: str, db: Session = Depends(get_db)) -> DecisionRead:
    decision = _service(db).get_decision(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision
