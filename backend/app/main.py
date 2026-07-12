"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api.v1.content import router as content_router
from backend.app.api.v1.decision import router as decision_router
from backend.app.api.v1.decisions_v1 import router as decision_api_v1_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.opportunities import router as opportunities_router
from backend.app.api.v1.ready import router as ready_router
from backend.app.api.v1.signals import router as signals_router
from backend.app.api.v1.signals_v1 import router as signals_api_v1_router
from backend.app.api.v1.topics_v1 import router as topics_api_v1_router
from backend.app.core.config import settings


def create_application() -> FastAPI:
    """Create the configured FastAPI application."""
    application = FastAPI(title=settings.app_name)
    application.include_router(health_router)
    application.include_router(ready_router)
    application.include_router(content_router)
    application.include_router(decision_router)
    application.include_router(opportunities_router)
    application.include_router(signals_router)
    application.include_router(signals_api_v1_router)
    application.include_router(decision_api_v1_router)
    application.include_router(topics_api_v1_router)
    return application


app = create_application()
