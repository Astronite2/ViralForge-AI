"""Health-check endpoint."""

from fastapi import APIRouter, status

from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def health_check() -> HealthResponse:
    """Return service liveness without touching external dependencies."""
    return HealthResponse(status="ok")
