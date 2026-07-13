"""Content opportunity read endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.schemas.opportunity import OpportunityRead
from backend.app.services.opportunity import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _service(db: Session) -> OpportunityService:
    return OpportunityService(db)


@router.get("", response_model=list[OpportunityRead])
def list_opportunities(
    limit: int = Query(default=settings.pagination_default_limit, ge=1),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[OpportunityRead]:
    """Return opportunity score history."""
    return _service(db).list_opportunities(
        min(limit, settings.pagination_max_limit), offset
    )
