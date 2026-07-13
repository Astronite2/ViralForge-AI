"""Configuration for deterministic opportunity scoring."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.core.config import settings


class OpportunityConfig(BaseSettings):
    """Validated opportunity weights and thresholds."""

    demand_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    growth_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    competition_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    evergreen_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    platform_fit_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    monetization_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    freshness_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    novelty_weight: float = Field(default=0.05, ge=0.0, le=1.0)
    version: str = settings.opportunity_engine_version

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="OPPORTUNITY_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_weight_total(self) -> "OpportunityConfig":
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.000001:
            raise ValueError("Opportunity weights must total 1.0")
        return self

    @property
    def weights(self) -> dict[str, float]:
        return {
            "demand": self.demand_weight,
            "growth": self.growth_weight,
            "competition": self.competition_weight,
            "evergreen": self.evergreen_weight,
            "platform_fit": self.platform_fit_weight,
            "monetization": self.monetization_weight,
            "freshness": self.freshness_weight,
            "novelty": self.novelty_weight,
        }
