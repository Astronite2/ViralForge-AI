"""Shared fixtures for backend tests."""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.db.base import Base


@pytest.fixture
def raw_content() -> dict[str, Any]:
    """Provide a valid platform-neutral connector payload."""
    return {
        "id": "youtube:abc123",
        "platform": "youtube",
        "creator_name": "ViralForge",
        "creator_id": "channel-1",
        "title": "Normalized Content",
        "description": "A platform-independent item.",
        "url": "https://example.com/watch/abc123",
        "language": "en",
        "country": "US",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "duration_seconds": 120,
        "content_type": "video",
        "metrics": {"views": 100.0},
        "analysis": {},
        "metadata": {"source": "test"},
    }


@pytest.fixture
def session() -> Session:
    """Provide an isolated in-memory SQLAlchemy session."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    database_session = session_factory()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
