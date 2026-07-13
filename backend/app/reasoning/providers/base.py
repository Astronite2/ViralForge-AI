"""Reasoning provider abstraction."""

from __future__ import annotations

from typing import Protocol

from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningProviderResponse,
    ReasoningRequest,
)


class ReasoningProvider(Protocol):
    """Provider contract for AI-assisted reasoning."""

    def generate_reasoning(
        self,
        context: ReasoningContext,
        request: ReasoningRequest,
    ) -> ReasoningProviderResponse:
        """Generate structured reasoning output."""
