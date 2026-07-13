"""Shared prompt helpers."""

from __future__ import annotations

import json
from dataclasses import asdict

from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningMessage,
    ReasoningRequest,
)

SYSTEM_PROMPT = (
    "You are ViralForge AI's reasoning layer. Use only the supplied facts and "
    "evidence. Never invent scores, sources, metrics, confidence, or history. "
    "If information is missing, say so explicitly. If evidence conflicts, preserve "
    "the conflict. Return strict JSON only."
)


def build_messages(
    instructions: str,
    context: ReasoningContext,
    request: ReasoningRequest,
) -> tuple[ReasoningMessage, ...]:
    """Build deterministic prompt messages."""
    user_payload = {
        "instructions": instructions,
        "context_version": context.context_version,
        "reasoning_type": request.reasoning_type.value,
        "context": _json_safe(asdict(context)),
    }
    return (
        ReasoningMessage(role="system", content=SYSTEM_PROMPT),
        ReasoningMessage(role="user", content=json.dumps(user_payload, sort_keys=True)),
    )


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, set):
        return sorted(_json_safe(item) for item in value)
    return value
