"""Opportunity score query service."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.opportunity_score import OpportunityScoreModel
from backend.app.schemas.opportunity import OpportunityRead


class OpportunityService:
    """Application service for opportunity history queries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_opportunities(self, limit: int, offset: int) -> list[OpportunityRead]:
        """Return opportunity history."""
        return [
            OpportunityRead.model_validate(opportunity)
            for opportunity in self.session.query(OpportunityScoreModel)
            .order_by(OpportunityScoreModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ]

    def list_topic_opportunities(
        self, topic_id: str, limit: int, offset: int
    ) -> list[OpportunityRead]:
        return [
            OpportunityRead.model_validate(opportunity)
            for opportunity in self.session.query(OpportunityScoreModel)
            .filter(OpportunityScoreModel.topic_id == topic_id)
            .order_by(OpportunityScoreModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ]
