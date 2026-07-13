"""Prompt template for opportunity comparisons."""

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
    """Build the opportunity comparison prompt."""
    instructions = (
        "Compare the supplied topics or opportunities using only the provided "
        "opportunity scores, decision scores, evidence, and history. Identify "
        "relative strengths, relative weaknesses, and caveats without inventing any "
        "facts."
    )
    return ReasoningPromptBundle(
        prompt_version=request.prompt_version,
        messages=build_messages(instructions, context, request),
    )
