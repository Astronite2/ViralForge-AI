"""Content intelligence repository tests."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.domain.content_opportunity import ContentOpportunity
from backend.app.domain.trend_signal import TrendSignal
from backend.app.pipeline.normalizer import ContentNormalizer
from backend.app.repositories.content import ContentRepository
from backend.app.repositories.historical_observation import (
    HistoricalObservationRepository,
)
from backend.app.repositories.opportunity import OpportunityRepository
from backend.app.repositories.opportunity_score import OpportunityScoreRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.topic_relationship import TopicRelationshipRepository
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


def test_knowledge_repositories_store_history_rows(session: Session) -> None:
    topic = TopicRepository(session).create("Ancient Egypt", "ancient egypt")

    observation_repo = HistoricalObservationRepository(session)
    opportunity_repo = OpportunityScoreRepository(session)
    relationship_repo = TopicRelationshipRepository(session)

    from backend.app.models.historical_observation import HistoricalObservationModel
    from backend.app.models.opportunity_score import OpportunityScoreModel
    from backend.app.models.topic_relationship import TopicRelationshipModel

    observation = HistoricalObservationModel(
        id="obs-test",
        topic_id=topic.id,
        source="google_trends",
        connector_name="google_trends",
        observation_type="signal",
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        correlation_id="correlation-test",
        observation_hash="hash-test",
        payload={"signal_score": 10.0},
        change_type="new",
    )
    observation_repo.create(observation)

    opportunity_repo.create(
        OpportunityScoreModel(
            id="opp-test",
            topic_id=topic.id,
            observation_id=observation.id,
            score=10.0,
            confidence=80.0,
            version="v1",
            dimensions={"demand": 10.0},
            explanations={"demand": "Test"},
            correlation_id="correlation-test",
        )
    )
    relationship_repo.create(
        TopicRelationshipModel(
            id="rel-test",
            source_topic_id=topic.id,
            target_topic_id=topic.id,
            relationship_type="related",
            strength=0.5,
            reason="Self relation for test",
            correlation_id="correlation-test",
        )
    )
    session.commit()

    assert len(observation_repo.list_by_topic(topic.id, 10, 0)) == 1
    assert len(opportunity_repo.list_by_topic(topic.id)) == 1
    assert len(relationship_repo.list_by_topic(topic.id)) == 1
