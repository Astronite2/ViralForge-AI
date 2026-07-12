"""Content opportunity read endpoints."""

from fastapi import APIRouter

from backend.app.schemas.opportunity import OpportunityRead
from backend.app.services.opportunity import OpportunityService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])
service = OpportunityService()


@router.get("", response_model=list[OpportunityRead])
def list_opportunities() -> list[OpportunityRead]:
    """Return content opportunity placeholders."""
    return service.list_opportunities()
