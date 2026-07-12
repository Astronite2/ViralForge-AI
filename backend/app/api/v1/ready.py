"""Readiness endpoint."""

from fastapi import APIRouter, Response, status

from backend.app.schemas.health import ReadyResponse
from backend.app.services.readiness import ReadinessService

router = APIRouter(tags=["readiness"])
service = ReadinessService()


@router.get("/ready", response_model=ReadyResponse)
def ready_check(response: Response) -> ReadyResponse:
    """Return service readiness for PostgreSQL and Redis."""
    result = service.check()
    if result.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status=result.status, postgres=result.postgres, redis=result.redis
    )
