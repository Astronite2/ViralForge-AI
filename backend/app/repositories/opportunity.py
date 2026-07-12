"""Content opportunity persistence access."""

from backend.app.domain.content_opportunity import ContentOpportunity
from backend.app.models.opportunity import OpportunityModel
from backend.app.repositories.base import Repository


class OpportunityRepository(Repository):
    """Database access boundary for opportunities."""

    def create(
        self, content_id: str, opportunity: ContentOpportunity
    ) -> OpportunityModel:
        """Store a content opportunity without committing the session."""
        model = OpportunityModel(
            content_id=content_id,
            score=opportunity.score,
            competition=opportunity.competition,
            growth_rate=opportunity.growth_rate,
            recommended_action=opportunity.recommended_action,
            estimated_rpm=opportunity.estimated_rpm,
            confidence=opportunity.confidence,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def list(self) -> list[OpportunityModel]:
        """Return all stored opportunities."""
        return list(self.session.query(OpportunityModel).order_by(OpportunityModel.id))
