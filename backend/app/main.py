"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.connectors import router as connectors_router
from backend.app.api.v1.content import router as content_router
from backend.app.api.v1.decision import router as decision_router
from backend.app.api.v1.decisions_v1 import router as decision_api_v1_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.history import router as history_router
from backend.app.api.v1.money_opportunities import router as money_opportunities_router
from backend.app.api.v1.opportunities import router as opportunities_router
from backend.app.api.v1.production_briefs import router as production_briefs_router
from backend.app.api.v1.projects import router as projects_router
from backend.app.api.v1.ready import router as ready_router
from backend.app.api.v1.reasoning import router as reasoning_router
from backend.app.api.v1.signals import router as signals_router
from backend.app.api.v1.signals_v1 import router as signals_api_v1_router
from backend.app.api.v1.topic_graph import router as topic_graph_router
from backend.app.api.v1.topics_v1 import router as topics_api_v1_router
from backend.app.core.config import settings


def create_application() -> FastAPI:
    """Create the configured FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(ready_router)
    application.include_router(reasoning_router)
    application.include_router(content_router)
    application.include_router(connectors_router)
    application.include_router(decision_router)
    application.include_router(opportunities_router)
    application.include_router(money_opportunities_router)
    application.include_router(projects_router)
    application.include_router(production_briefs_router)
    application.include_router(signals_router)
    application.include_router(signals_api_v1_router)
    application.include_router(decision_api_v1_router)
    application.include_router(history_router)
    application.include_router(topic_graph_router)
    application.include_router(topics_api_v1_router)

    return application


app = create_application()
