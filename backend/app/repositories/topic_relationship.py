"""Topic graph relationship persistence access."""

from __future__ import annotations

from backend.app.models.topic_relationship import TopicRelationshipModel
from backend.app.repositories.base import Repository


class TopicRelationshipRepository(Repository):
    """Database access boundary for topic graph edges."""

    def create(self, model: TopicRelationshipModel) -> TopicRelationshipModel:
        self.session.add(model)
        self.session.flush()
        return model

    def get(
        self,
        source_topic_id: str,
        target_topic_id: str,
        relationship_type: str,
    ) -> TopicRelationshipModel | None:
        query = self.session.query(TopicRelationshipModel).filter(
            TopicRelationshipModel.source_topic_id == source_topic_id,
            TopicRelationshipModel.target_topic_id == target_topic_id,
            TopicRelationshipModel.relationship_type == relationship_type,
        )
        return query.one_or_none()

    def list_by_topic(self, topic_id: str) -> list[TopicRelationshipModel]:
        query = (
            self.session.query(TopicRelationshipModel)
            .filter(
                (TopicRelationshipModel.source_topic_id == topic_id)
                | (TopicRelationshipModel.target_topic_id == topic_id)
            )
            .order_by(TopicRelationshipModel.strength.desc())
        )
        return list(query)
