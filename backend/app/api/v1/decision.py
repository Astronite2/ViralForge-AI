"""Decision Engine endpoints."""

from fastapi import APIRouter

from backend.app.schemas.decision import DecisionRead
from backend.app.services.decision import DecisionService

router = APIRouter(prefix="/decision", tags=["decision"])
service = DecisionService()


@router.get("/demo", response_model=DecisionRead)
def decision_demo() -> DecisionRead:
    """Return a fully traceable deterministic decision using placeholder data."""
    return DecisionRead.model_validate(service.demo())
