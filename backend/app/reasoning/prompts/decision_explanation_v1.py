"""Prompt template for decision explanations."""

from __future__ import annotations

from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningPromptBundle,
    ReasoningRequest,
)
from backend.app.reasoning.prompts.common import build_messages


def build_prompt(
    context: ReasoningContext, request: ReasoningRequest
) -> ReasoningPromptBundle:
    """Build the decision explanation prompt."""
    instructions = (
        "Explain the stored decision in plain language. Cite evidence IDs in each "
        "factual claim. Answer why now, why this topic, why this platform, and how "
        "confident we are. Do not change the stored decision."
    )
    return ReasoningPromptBundle(
        prompt_version=request.prompt_version,
        messages=build_messages(instructions, context, request),
    )
