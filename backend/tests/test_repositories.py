"""Content intelligence repository tests."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.domain.content_opportunity import ContentOpportunity
from backend.app.domain.trend_signal import TrendSignal
from backend.app.pipeline.normalizer import ContentNormalizer
from backend.app.repositories.content import ContentRepository
from backend.app.repositories.opportunity import OpportunityRepository
from backend.app.repositories.trend import TrendRepository


def test_content_repository_stores_content(
    session: Session, raw_content: dict[str, Any]
) -> None:
    content = ContentNormalizer().normalize(raw_content)
    repository = ContentRepository(session)

    repository.upsert(content)
    session.commit()

    stored = repository.get(content.id)
    assert stored is not None
    assert stored.title == content.title
    assert stored.metadata_ == {"source": "test"}


def test_signal_and_opportunity_repositories_store_pipeline_results(
    session: Session, raw_content: dict[str, Any]
) -> None:
    content = ContentNormalizer().normalize(raw_content)
    ContentRepository(session).upsert(content)
    signal = TrendSignal(
        source="test",
        score=0.5,
        confidence=0.8,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        reason="Test signal",
    )
    opportunity = ContentOpportunity(
        score=0.5,
        competition=0.2,
        growth_rate=0.3,
        recommended_action="Monitor",
        estimated_rpm=None,
        confidence=0.8,
    )
    trend_repository = TrendRepository(session)
    opportunity_repository = OpportunityRepository(session)

    trend_repository.create(content.id, signal)
    opportunity_repository.create(content.id, opportunity)
    session.commit()

    assert len(trend_repository.list()) == 1
    assert len(opportunity_repository.list()) == 1
