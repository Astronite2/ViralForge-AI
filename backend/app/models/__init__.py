"""SQLAlchemy persistence models."""

from backend.app.db.base import Base
from backend.app.models.analysis import Analysis
from backend.app.models.channel import Channel
from backend.app.models.content import ContentModel
from backend.app.models.decision import DecisionModel
from backend.app.models.decision_explanation import DecisionExplanationModel
from backend.app.models.evidence import EvidenceModel
from backend.app.models.historical_evidence import HistoricalEvidenceModel
from backend.app.models.historical_observation import HistoricalObservationModel
from backend.app.models.metric import Metric
from backend.app.models.money_opportunity import (
    MoneyAnalysisModel,
    MoneyOpportunityModel,
    MoneyOutcomeModel,
    ProductionBriefModel,
)
from backend.app.models.opportunity import Opportunity, OpportunityModel
from backend.app.models.opportunity_score import OpportunityScoreModel
from backend.app.models.platform import Platform
from backend.app.models.processed_event import ProcessedEventModel
from backend.app.models.production_brief import ProjectProductionBriefModel
from backend.app.models.project import ProjectModel
from backend.app.models.reasoning import (
    ReasoningResultModel,
    ReasoningRunModel,
    ReasoningSourceLinkModel,
    ReasoningValidationErrorModel,
)
from backend.app.models.research import ProjectResearchDossierModel
from backend.app.models.topic import Topic
from backend.app.models.topic_relationship import TopicRelationshipModel
from backend.app.models.trend_signal import TrendSignalModel
from backend.app.models.user import User
from backend.app.models.video import Video

__all__ = [
    "Analysis",
    "Base",
    "Channel",
    "ContentModel",
    "DecisionExplanationModel",
    "DecisionModel",
    "EvidenceModel",
    "HistoricalEvidenceModel",
    "HistoricalObservationModel",
    "Metric",
    "MoneyAnalysisModel",
    "MoneyOpportunityModel",
    "MoneyOutcomeModel",
    "Opportunity",
    "OpportunityModel",
    "OpportunityScoreModel",
    "Platform",
    "ProcessedEventModel",
    "ProjectProductionBriefModel",
    "ProductionBriefModel",
    "ProjectModel",
    "ProjectResearchDossierModel",
    "ReasoningResultModel",
    "ReasoningRunModel",
    "ReasoningSourceLinkModel",
    "ReasoningValidationErrorModel",
    "Topic",
    "TopicRelationshipModel",
    "TrendSignalModel",
    "User",
    "Video",
]
