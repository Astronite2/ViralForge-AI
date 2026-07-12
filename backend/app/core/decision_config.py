"""Configuration for deterministic decision scoring."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.core.config import settings


class DecisionConfig(BaseSettings):
    """Validated decision weights and action thresholds loaded from settings."""

    trend_momentum_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    audience_demand_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    revenue_potential_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    competition_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    evergreen_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    platform_fit_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    confidence_weight: float = Field(default=0.05, ge=0.0, le=1.0)
    create_threshold: float = Field(default=70.0, ge=0.0, le=100.0)
    review_threshold: float = Field(default=50.0, ge=0.0, le=100.0)
    wait_threshold: float = Field(default=30.0, ge=0.0, le=100.0)
    version: str = settings.decision_engine_version

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DECISION_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_weight_total(self) -> "DecisionConfig":
        """Ensure factor weights add up to a complete score."""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.000001:
            raise ValueError("Decision weights must total 1.0")
        return self

    @property
    def weights(self) -> dict[str, float]:
        """Return scoring weights keyed by stable factor identifiers."""
        return {
            "trend_momentum": self.trend_momentum_weight,
            "audience_demand": self.audience_demand_weight,
            "revenue_potential": self.revenue_potential_weight,
            "competition": self.competition_weight,
            "evergreen": self.evergreen_weight,
            "platform_fit": self.platform_fit_weight,
            "confidence": self.confidence_weight,
        }
