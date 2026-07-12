"""Opportunity scoring pipeline placeholder."""

from backend.app.domain.content import Content
from backend.app.domain.content_opportunity import ContentOpportunity


class OpportunityStage:
    """Create an unscored opportunity until scoring is configured."""

    def process(self, content: Content) -> ContentOpportunity:
        """Return a placeholder opportunity for normalized content."""
        return ContentOpportunity(
            score=0.0,
            competition=0.0,
            growth_rate=0.0,
            recommended_action="No recommendation available.",
            estimated_rpm=None,
            confidence=0.0,
        )
