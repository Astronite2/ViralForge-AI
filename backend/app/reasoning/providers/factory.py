"""Reasoning provider selection."""

from __future__ import annotations

from backend.app.core.config import settings
from backend.app.reasoning.errors import ReasoningConfigurationError
from backend.app.reasoning.providers.base import ReasoningProvider
from backend.app.reasoning.providers.openai_compatible import (
    OpenAICompatibleReasoningProvider,
)


def build_reasoning_provider() -> ReasoningProvider:
    """Build the configured reasoning provider."""
    if not settings.ai_reasoning_enabled:
        raise ReasoningConfigurationError("AI reasoning is disabled")

    api_key = settings.ai_api_key or settings.openai_api_key
    if not api_key:
        raise ReasoningConfigurationError("AI reasoning API key is missing")

    if not settings.ai_model:
        raise ReasoningConfigurationError("AI reasoning model is missing")

    provider_name = settings.ai_provider.lower().strip()
    if provider_name != "openai":
        raise ReasoningConfigurationError(
            f"Unsupported reasoning provider: {settings.ai_provider}"
        )

    return OpenAICompatibleReasoningProvider(
        api_key=api_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
        max_output_tokens=settings.ai_max_output_tokens,
        temperature=settings.ai_temperature,
    )
