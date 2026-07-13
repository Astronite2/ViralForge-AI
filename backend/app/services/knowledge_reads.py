"""Read-only knowledge-layer queries."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.repositories.topic import TopicRepository
from backend.app.services.knowledge_layer import KnowledgeLayerService


class KnowledgeReadService:
    """Expose historical memory and topic graph state."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.topic_repository = TopicRepository(session)
        self.knowledge_layer = KnowledgeLayerService(session)

    def get_history(self, topic_id: str) -> dict[str, object] | None:
        topic = self.topic_repository.get_by_id(topic_id)
        if topic is None:
            return None
        history = self.knowledge_layer.history_for_topic(topic_id)
        return {
            "topic": topic,
            "observations": history.observations,
            "analytics": history.analytics,
            "opportunity_scores": history.opportunity_scores,
            "evidence_history": history.evidence_history,
        }

    def get_topic_graph(self, topic_id: str) -> dict[str, object] | None:
        topic = self.topic_repository.get_by_id(topic_id)
        if topic is None:
            return None
        relationships = self.knowledge_layer.graph_for_topic(topic_id)
        return {"topic": topic, "relationships": relationships}
