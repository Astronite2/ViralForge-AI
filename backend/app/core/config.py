"""Environment-based application settings."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated configuration loaded from environment variables."""

    app_name: str = "ViralForge AI API"
    environment: Environment = Environment.DEVELOPMENT
    database_url: str = (
        "postgresql+psycopg://viralforge:viralforge@localhost:5432/viralforge"
    )
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = Field(default="development-secret-key", min_length=1)
    jwt_secret: str = Field(default="development-jwt-secret", min_length=1)
    openai_api_key: str | None = None
    youtube_api_key: str | None = None
    postgres_db: str = "viralforge"
    postgres_user: str = "viralforge"
    postgres_password: str = "viralforge"
    pagination_default_limit: int = Field(default=20, ge=1, le=1000)
    pagination_max_limit: int = Field(default=100, ge=1, le=1000)
    processing_retry_limit: int = Field(default=3, ge=0, le=10)
    processing_retry_delay_seconds: int = Field(default=30, ge=1, le=3600)
    polling_batch_size: int = Field(default=10, ge=1, le=1000)
    google_trends_poll_interval_minutes: int = Field(default=5, ge=1, le=1440)
    google_trends_enabled: bool = True
    google_trends_provider: str = "pytrends"
    google_trends_default_geo: str = "US"
    google_trends_default_timeframe: str = "today 7-d"
    google_trends_max_results: int = Field(default=10, ge=1, le=100)
    google_trends_retries: int = Field(default=2, ge=0, le=10)
    google_trends_backoff_seconds: float = Field(default=1.0, ge=0.0, le=60.0)
    google_trends_official_project_id: str | None = None
    google_trends_official_credentials_file: str | None = None
    google_trends_official_api_endpoint: str | None = None
    google_trends_official_access_enabled: bool = False
    connector_status_active_window_minutes: int = Field(default=60, ge=1, le=10080)
    decision_engine_version: str = "v1"
    event_version: str = "v1"
    opportunity_engine_version: str = "v1"
    knowledge_history_limit: int = Field(default=3650, ge=1, le=100000)
    knowledge_graph_limit: int = Field(default=100, ge=1, le=1000)
    reasoning_context_version: str = "v1"
    ai_reasoning_enabled: bool = False
    ai_provider: str = "openai"
    ai_model: str = ""
    ai_api_key: str | None = None
    ai_base_url: str = "https://api.openai.com/v1"
    ai_timeout_seconds: float = Field(default=30.0, gt=0.0, le=120.0)
    ai_max_retries: int = Field(default=2, ge=0, le=10)
    ai_max_context_tokens: int = Field(default=12000, ge=0, le=100000)
    ai_max_output_tokens: int = Field(default=1500, ge=1, le=100000)
    ai_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    ai_reasoning_prompt_version: str = "v1"
    ai_max_evidence_items: int = Field(default=24, ge=1, le=500)
    ai_max_historical_observations: int = Field(default=50, ge=1, le=1000)
    ai_max_comparison_topics: int = Field(default=5, ge=2, le=20)
    ai_max_response_bytes: int = Field(default=200_000, ge=1, le=5_000_000)
    ai_estimated_cost_input_per_1k_tokens: float = Field(default=0.0, ge=0.0, le=1000.0)
    ai_estimated_cost_output_per_1k_tokens: float = Field(
        default=0.0, ge=0.0, le=1000.0
    )
    neutral_factor_defaults: dict[str, float] = Field(
        default_factory=lambda: {
            "trend_momentum": 50.0,
            "audience_demand": 50.0,
            "revenue_potential": 50.0,
            "competition": 50.0,
            "evergreen": 50.0,
            "platform_fit": 50.0,
        }
    )
    evidence_factor_rules: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "google_trends": [
                "trend_momentum",
                "audience_demand",
                "confidence",
                "revenue_potential",
                "competition",
                "evergreen",
                "platform_fit",
            ]
        }
    )
    google_trends_source_name: str = "google_trends"
    youtube_source_name: str = "youtube"
    youtube_default_region: str = "US"
    youtube_default_limit: int = Field(default=10, ge=1, le=50)
    youtube_api_base_url: str = "https://www.googleapis.com/youtube/v3"
    youtube_timeout_seconds: float = Field(default=10.0, gt=0.0, le=60.0)
    reddit_enabled: bool = False
    reddit_provider: str = "official"
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_username: str | None = None
    reddit_password: str | None = None
    reddit_user_agent: str = Field(default="ViralForgeAI/0.1", min_length=5)
    reddit_default_subreddits: str = ""
    reddit_default_query: str = ""
    reddit_default_sort: str = "hot"
    reddit_default_time_filter: str = "week"
    reddit_default_limit: int = Field(default=25, ge=1, le=100)
    reddit_timeout_seconds: float = Field(default=20.0, gt=0.0, le=120.0)
    reddit_max_retries: int = Field(default=2, ge=0, le=10)
    reddit_backoff_seconds: float = Field(default=1.0, ge=0.0, le=60.0)
    reddit_source_name: str = "reddit"
    money_engine_version: str = "money-v1"
    revenue_benchmark_version: str = "rpm-benchmarks-v1"
    money_opportunity_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "demand": 0.14,
            "momentum": 0.10,
            "competition_opportunity": 0.10,
            "evergreen": 0.10,
            "advertiser_value": 0.12,
            "audience_value": 0.08,
            "watch_time_potential": 0.07,
            "click_through_potential": 0.06,
            "production_feasibility": 0.08,
            "monetization_safety": 0.07,
            "evidence_confidence": 0.05,
            "channel_fit": 0.03,
        }
    )
    rpm_benchmarks: dict[str, tuple[float, float, float]] = Field(
        default_factory=lambda: {
            "entertainment": (1.0, 2.5, 4.5),
            "history": (1.5, 3.5, 6.0),
            "education": (2.0, 4.5, 8.0),
            "technology": (2.5, 6.0, 12.0),
            "finance": (5.0, 12.0, 22.0),
            "business": (4.0, 9.0, 16.0),
            "careers": (3.0, 7.0, 12.0),
            "travel": (1.5, 4.0, 8.0),
            "gaming": (0.8, 2.2, 4.5),
            "general": (1.0, 3.0, 6.0),
        }
    )
    research_search_provider: str = "met_crossref_wikipedia"
    research_search_api_url: str | None = None
    research_search_api_key: str | None = None
    research_max_search_queries: int = Field(default=12, ge=1, le=30)
    research_max_sources: int = Field(default=30, ge=1, le=100)
    research_min_authoritative_sources: int = Field(default=3, ge=0, le=30)
    research_timeout_seconds: float = Field(default=180.0, gt=0.0, le=600.0)
    research_max_retries: int = Field(default=1, ge=0, le=5)
    research_version: str = "research-v1"
    production_brief_version: str = "producer-v1"
    script_version: str = "script-v1"
    script_words_per_minute: int = Field(default=145, ge=100, le=220)
    script_word_count_tolerance: float = Field(default=0.10, ge=0.0, le=0.5)
    script_allow_limited_evidence: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached process-wide settings."""
    return Settings()


settings = get_settings()
