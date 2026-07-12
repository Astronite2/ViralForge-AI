"""Analysis pipeline placeholder."""

from dataclasses import replace

from backend.app.domain.content import Content
from backend.app.pipeline.base import ContentStage


class AnalysisStage(ContentStage):
    """Attach a placeholder analysis state without AI processing."""

    def process(self, content: Content) -> Content:
        """Record that analysis is intentionally not implemented."""
        return replace(content, analysis={**content.analysis, "status": "pending"})
