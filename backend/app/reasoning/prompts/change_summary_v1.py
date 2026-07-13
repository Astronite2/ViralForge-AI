"""Prompt template for change summaries."""

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
    """Build the change summary prompt."""
    instructions = (
        "Summarize what changed since the previous decision or previous reasoning "
        "result. Focus on deterministic differences in signals, evidence, "
        "opportunity scores, and decisions."
    )
    return ReasoningPromptBundle(
        prompt_version=request.prompt_version,
        messages=build_messages(instructions, context, request),
    )
