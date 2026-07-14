"""Money-opportunity workflow request and response contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from backend.app.schemas.base import Schema


class ChannelProfileInput(Schema):
    channel_name: str = "Default channel"
    niche: str | None = None
    target_countries: list[str] = []
    preferred_video_length: int | None = Field(default=None, ge=1, le=240)
    production_capacity_per_week: int | None = Field(default=None, ge=1, le=50)
    maximum_production_hours_per_video: float | None = Field(default=None, gt=0, le=500)
    preferred_content_style: str | None = None
    language: str | None = None
    monetization_status: str | None = None
    subscriber_count: int | None = Field(default=None, ge=0)
    average_views: int | None = Field(default=None, ge=0)
    excluded_topics: list[str] = []
    risk_tolerance: Literal["low", "medium", "high"] = "medium"


class MoneyAnalysisRequest(Schema):
    query: str = Field(min_length=2, max_length=200)
    region: str = Field(default="US", min_length=2, max_length=8)
    limit: int = Field(default=25, ge=3, le=50)
    channel_profile_id: str | None = None
    channel_profile: ChannelProfileInput | None = None


class RangeEstimate(Schema):
    low: float | None
    base: float | None
    high: float | None
    basis: Literal[
        "observed", "benchmark", "observed_views_benchmark_rpm", "unavailable"
    ]


class MoneyOpportunityRead(Schema):
    id: str
    analysis_id: str
    rank: int
    topic: str
    proposed_video_angle: str
    money_score: float
    confidence: float
    opportunity_type: str
    demand_score: float
    momentum_score: float
    competition_score: float
    evergreen_score: float
    advertiser_value_score: float
    audience_value_score: float
    watch_time_potential: float
    click_through_potential: float
    production_difficulty: float
    monetization_safety: float
    evidence_confidence: float
    channel_fit_score: float | None
    estimated_production_hours: float
    estimated_views: RangeEstimate
    estimated_rpm: RangeEstimate
    estimated_revenue: RangeEstimate
    expected_opportunity_window: str
    monetization_risks: list[str]
    evidence_summary: list[str]
    evidence_references: list[dict[str, Any]]
    explanation: str
    assumptions: list[str]
    limitations: list[str]
    weights: dict[str, float]
    calculation_trace: list[dict[str, Any]]
    engine_version: str


class MoneyAnalysisRead(Schema):
    analysis_id: str
    query: str
    region: str
    status: str
    created_at: datetime
    opportunities: list[MoneyOpportunityRead]


class ProductionBriefRead(Schema):
    id: str
    opportunity_id: str
    recommended_title_options: list[str]
    primary_angle: str
    target_viewer: str
    viewer_promise: str
    hook_options: list[str]
    suggested_duration: str
    section_outline: list[str]
    evidence_backed_facts_to_research: list[dict[str, Any]]
    thumbnail_concepts: list[str]
    thumbnail_text_options: list[str]
    keywords: list[str]
    description_outline: list[str]
    monetization_risks: list[str]
    copyright_risks: list[str]
    production_difficulty: float
    estimated_production_hours: float
    publishing_recommendation: str
    limitations: list[str]


class OutcomeCreate(Schema):
    publish_status: str = "planned"
    youtube_video_id: str | None = None
    publication_date: datetime | None = None
    production_hours: float | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)
    user_notes: str | None = None


class OutcomeUpdate(Schema):
    publish_status: str | None = None
    youtube_video_id: str | None = None
    publication_date: datetime | None = None
    production_hours: float | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)
    views_after_24_hours: int | None = Field(default=None, ge=0)
    views_after_7_days: int | None = Field(default=None, ge=0)
    views_after_30_days: int | None = Field(default=None, ge=0)
    watch_time_hours: float | None = Field(default=None, ge=0)
    ctr: float | None = Field(default=None, ge=0, le=1)
    subscribers_gained: int | None = Field(default=None, ge=0)
    rpm: float | None = Field(default=None, ge=0)
    revenue: float | None = Field(default=None, ge=0)
    user_notes: str | None = None
    result_classification: (
        Literal["pending", "underperformed", "met_expectation", "outperformed"] | None
    ) = None


class OutcomeRead(OutcomeUpdate):
    id: str
    recommendation_id: str
    selected_topic: str
    money_score_at_selection: float
    publish_status: str
    result_classification: str
    created_at: datetime
