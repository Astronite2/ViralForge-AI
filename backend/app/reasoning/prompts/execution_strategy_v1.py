"""Prompt template for execution strategies."""

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
    """Build the execution strategy prompt."""
    instructions = (
        "Recommend an execution strategy for the approved decision. Include content "
        "angle, target platform, format, urgency, timing, supporting formats, and "
        "risks. Do not generate a script and do not change the decision."
    )
    return ReasoningPromptBundle(
        prompt_version=request.prompt_version,
        messages=build_messages(instructions, context, request),
    )
