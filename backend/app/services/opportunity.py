"""Content opportunity query service."""

from backend.app.schemas.opportunity import OpportunityRead


class OpportunityService:
    """Application service for placeholder opportunity read operations."""

    def list_opportunities(self) -> list[OpportunityRead]:
        """Return placeholder opportunities until query persistence is enabled."""
        return []
