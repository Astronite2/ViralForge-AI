"""Opportunity score persistence access."""

from __future__ import annotations

from backend.app.models.opportunity_score import OpportunityScoreModel
from backend.app.repositories.base import Repository


class OpportunityScoreRepository(Repository):
    """Database access boundary for opportunity score history."""

    def create(self, model: OpportunityScoreModel) -> OpportunityScoreModel:
        self.session.add(model)
        self.session.flush()
        return model

    def list_by_topic(self, topic_id: str) -> list[OpportunityScoreModel]:
        query = (
            self.session.query(OpportunityScoreModel)
            .filter(OpportunityScoreModel.topic_id == topic_id)
            .order_by(OpportunityScoreModel.created_at.desc())
        )
        return list(query)

    def latest_by_topic(self, topic_id: str) -> OpportunityScoreModel | None:
        query = (
            self.session.query(OpportunityScoreModel)
            .filter(OpportunityScoreModel.topic_id == topic_id)
            .order_by(OpportunityScoreModel.created_at.desc())
        )
        return query.first()

    def get_by_observation(self, observation_id: str) -> OpportunityScoreModel | None:
        query = self.session.query(OpportunityScoreModel).filter(
            OpportunityScoreModel.observation_id == observation_id
        )
        return query.one_or_none()
