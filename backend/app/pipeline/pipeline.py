"""Orchestration for normalized content processing."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from backend.app.domain.content import Content
from backend.app.domain.content_opportunity import ContentOpportunity
from backend.app.models.content import ContentModel
from backend.app.pipeline.analysis import AnalysisStage
from backend.app.pipeline.enrichment import ContentEnrichment
from backend.app.pipeline.normalizer import ContentNormalizer
from backend.app.pipeline.opportunity import OpportunityStage
from backend.app.pipeline.persist import PersistStage
from backend.app.pipeline.signal_engine import SignalEngine
from backend.app.pipeline.validator import ContentValidator


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Results produced by one pipeline execution."""

    content: Content
    opportunity: ContentOpportunity
    persisted_content: ContentModel | None


class ContentPipeline:
    """Shared connector-agnostic normalized content pipeline."""

    def __init__(self, persist_stage: PersistStage | None = None) -> None:
        self.validator = ContentValidator()
        self.normalizer = ContentNormalizer()
        self.enrichment = ContentEnrichment()
        self.signal_engine = SignalEngine()
        self.analysis = AnalysisStage()
        self.opportunity = OpportunityStage()
        self.persist_stage = persist_stage

    def process(self, raw_content: Mapping[str, Any]) -> PipelineResult:
        """Validate, normalize, enrich, analyze, score, and optionally persist data."""
        self.validator.validate(raw_content)
        content = self.normalizer.normalize(raw_content)
        return self.process_normalized(content)

    def process_normalized(self, content: Content) -> PipelineResult:
        """Run the remaining pipeline stages for already normalized content."""
        content = self.enrichment.process(content)
        content = self.signal_engine.process(content)
        content = self.analysis.process(content)
        opportunity = self.opportunity.process(content)
        persisted_content = (
            self.persist_stage.process(content, opportunity)
            if self.persist_stage is not None
            else None
        )
        return PipelineResult(content, opportunity, persisted_content)
