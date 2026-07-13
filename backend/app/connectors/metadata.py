"""Typed metadata and capability discovery for Connector SDK v2."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator


class ConnectorCapability(StrEnum):
    SEARCH = "SEARCH"
    TRENDING = "TRENDING"
    HISTORICAL = "HISTORICAL"
    REALTIME = "REALTIME"
    COMMENTS = "COMMENTS"
    CHANNELS = "CHANNELS"
    COMMUNITIES = "COMMUNITIES"
    AUTHORS = "AUTHORS"
    ENGAGEMENT_METRICS = "ENGAGEMENT_METRICS"
    AUDIENCE_SIGNALS = "AUDIENCE_SIGNALS"
    MONETIZATION_SIGNALS = "MONETIZATION_SIGNALS"
    GEO_FILTERING = "GEO_FILTERING"
    LANGUAGE_FILTERING = "LANGUAGE_FILTERING"
    DATE_FILTERING = "DATE_FILTERING"
    KEYWORD_MONITORING = "KEYWORD_MONITORING"
    TOPIC_MONITORING = "TOPIC_MONITORING"
    FORECAST_INPUT = "FORECAST_INPUT"
    CONTENT_DISCOVERY = "CONTENT_DISCOVERY"


CAPABILITY_DESCRIPTIONS: dict[ConnectorCapability, str] = {
    capability: capability.value.replace("_", " ").capitalize()
    for capability in ConnectorCapability
}


class ConnectorCapabilities(BaseModel):
    """Deterministically ordered set of capabilities."""

    model_config = ConfigDict(frozen=True, use_enum_values=False)
    values: tuple[ConnectorCapability, ...] = ()

    @field_validator("values", mode="before")
    @classmethod
    def normalize(cls, value: object) -> tuple[ConnectorCapability, ...]:
        if value is None:
            return ()
        members = {ConnectorCapability(item) for item in value}  # type: ignore[arg-type]
        return tuple(item for item in ConnectorCapability if item in members)

    def __contains__(self, capability: object) -> bool:
        try:
            member = ConnectorCapability(capability)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False
        return member in self.values

    def supports(self, capability: ConnectorCapability | str) -> bool:
        return capability in self

    def api_values(self) -> tuple[str, ...]:
        return tuple(item.value for item in self.values)

    @classmethod
    def of(cls, *values: ConnectorCapability) -> Self:
        return cls(values=values)


class ConnectorMetadata(BaseModel):
    """Public, non-sensitive description of a connector implementation."""

    model_config = ConfigDict(frozen=True)
    name: str
    display_name: str
    version: str
    provider: str
    provider_experimental: bool = False
    description: str
    capabilities: ConnectorCapabilities = ConnectorCapabilities()
    supports_live_access: bool
    supports_fixture_access: bool
