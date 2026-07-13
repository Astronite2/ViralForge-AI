"""CI-only PostgreSQL persistence and application readiness smoke test."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.domain.content import Content
from backend.app.main import app
from backend.app.repositories.content import ContentRepository


def main() -> None:
    """Verify migrated PostgreSQL persistence plus liveness and readiness."""
    content_id = f"ci:{uuid4()}"
    content = Content(
        id=content_id,
        platform="ci",
        creator_name="CI",
        creator_id="ci",
        title="PostgreSQL smoke test",
        description="Disposable CI persistence record.",
        url="https://example.invalid/ci",
        language="en",
        country=None,
        published_at=datetime.now(UTC),
        duration_seconds=None,
        content_type="smoke_test",
        metrics={"iteration": 1.0},
    )

    with SessionLocal.begin() as session:
        repository = ContentRepository(session)
        repository.save(content)
        repository.save(
            replace(
                content,
                title="PostgreSQL smoke test updated",
                metrics={"iteration": 2.0},
            )
        )

    with SessionLocal() as session:
        repository = ContentRepository(session)
        stored = repository.get(content_id)
        assert stored is not None
        assert stored.title == "PostgreSQL smoke test updated"
        assert stored.metrics == {"iteration": 2.0}
        assert len([item for item in repository.list() if item.id == content_id]) == 1

    with TestClient(app) as client:
        health = client.get("/health")
        readiness = client.get("/ready")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        assert readiness.status_code == 200
        assert readiness.json() == {
            "status": "ready",
            "postgres": "ok",
            "redis": "ok",
        }


if __name__ == "__main__":
    main()
