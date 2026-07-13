"""Pure domain objects independent of infrastructure."""

from backend.app.domain.analysis_result import AnalysisResult
from backend.app.domain.connector_orchestration import (
    ConnectorExecutionReport,
    ConnectorOrchestrationReport,
)
from backend.app.domain.content import Content
from backend.app.domain.content_opportunity import ContentOpportunity
from backend.app.domain.decision import Decision
from backend.app.domain.decision_calculated import DecisionCalculated
from backend.app.domain.decision_enums import DecisionType, SignalStrength
from backend.app.domain.decision_explanation import DecisionExplanation
from backend.app.domain.evidence import Evidence
from backend.app.domain.knowledge import (
    HistoricalAnalytics,
    HistoricalEvidenceSnapshot,
    HistoricalObservation,
    OpportunityScore,
    TopicRelationship,
    TopicRelationshipType,
)
from backend.app.domain.platform_content import PlatformContent
from backend.app.domain.reasoning import (
    ReasoningAlternativeTopicComparison,
    ReasoningContext,
    ReasoningEvidenceReference,
    ReasoningMessage,
    ReasoningPromptBundle,
    ReasoningProviderResponse,
    ReasoningRequest,
    ReasoningResult,
    ReasoningRun,
    ReasoningStatus,
    ReasoningType,
    ReasoningValidationIssue,
)
from backend.app.domain.topic import Topic
from backend.app.domain.trend_signal import TrendSignal
from backend.app.domain.unified_signal import SignalType, UnifiedSignal

__all__ = [
    "AnalysisResult",
    "ConnectorExecutionReport",
    "ConnectorOrchestrationReport",
    "Content",
    "ContentOpportunity",
    "Decision",
    "DecisionCalculated",
    "DecisionExplanation",
    "DecisionType",
    "Evidence",
    "HistoricalAnalytics",
    "HistoricalEvidenceSnapshot",
    "HistoricalObservation",
    "PlatformContent",
    "ReasoningAlternativeTopicComparison",
    "ReasoningContext",
    "ReasoningEvidenceReference",
    "ReasoningMessage",
    "ReasoningPromptBundle",
    "ReasoningProviderResponse",
    "ReasoningRequest",
    "ReasoningResult",
    "ReasoningRun",
    "ReasoningStatus",
    "ReasoningValidationIssue",
    "ReasoningType",
    "OpportunityScore",
    "Topic",
    "TopicRelationship",
    "TopicRelationshipType",
    "SignalStrength",
    "TrendSignal",
    "SignalType",
    "UnifiedSignal",
]
