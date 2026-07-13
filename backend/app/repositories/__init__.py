"""Repository layer for database access."""

from backend.app.repositories.content import ContentRepository
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.decision_explanation import DecisionExplanationRepository
from backend.app.repositories.evidence import EvidenceRepository
from backend.app.repositories.opportunity import OpportunityRepository
from backend.app.repositories.processed_event import ProcessedEventRepository
from backend.app.repositories.reasoning import (
    ReasoningResultRepository,
    ReasoningRunRepository,
    ReasoningSourceLinkRepository,
    ReasoningValidationErrorRepository,
)
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.trend import TrendRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.repositories.user import UserRepository
from backend.app.repositories.video import VideoRepository

__all__ = [
    "ContentRepository",
    "DecisionExplanationRepository",
    "DecisionRepository",
    "EvidenceRepository",
    "OpportunityRepository",
    "ProcessedEventRepository",
    "ReasoningResultRepository",
    "ReasoningRunRepository",
    "ReasoningSourceLinkRepository",
    "ReasoningValidationErrorRepository",
    "TopicRepository",
    "TrendRepository",
    "TrendSignalRepository",
    "UserRepository",
    "VideoRepository",
]
