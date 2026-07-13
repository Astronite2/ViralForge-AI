"""Pipeline persistence stage."""

from backend.app.domain.content import Content
from backend.app.domain.content_opportunity import ContentOpportunity
from backend.app.models.content import ContentModel
from backend.app.repositories.content import ContentRepository
from backend.app.repositories.opportunity import OpportunityRepository
from backend.app.repositories.trend import TrendRepository


class PersistStage:
    """Persist pipeline results through repository boundaries."""

    def __init__(
        self,
        content_repository: ContentRepository,
        trend_repository: TrendRepository,
        opportunity_repository: OpportunityRepository,
    ) -> None:
        self.content_repository = content_repository
        self.trend_repository = trend_repository
        self.opportunity_repository = opportunity_repository

    def process(
        self, content: Content, opportunity: ContentOpportunity
    ) -> ContentModel:
        """Store content, its signals, and its opportunity in one transaction."""
        content_model = self.content_repository.save(content)
        for signal in content.signals:
            self.trend_repository.create(content.id, signal)
        self.opportunity_repository.create(content.id, opportunity)
        self.content_repository.session.commit()
        return content_model
