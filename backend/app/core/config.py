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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached process-wide settings."""
    return Settings()


settings = get_settings()
