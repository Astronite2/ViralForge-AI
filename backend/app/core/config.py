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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached process-wide settings."""
    return Settings()


settings = get_settings()
