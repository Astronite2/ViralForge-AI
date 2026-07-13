"""OpenAI-compatible reasoning provider."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable

import httpx

from backend.app.core.config import settings
from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningProviderResponse,
    ReasoningRequest,
)
from backend.app.reasoning.errors import ReasoningTransientProviderError

logger = logging.getLogger(__name__)


class OpenAICompatibleReasoningProvider:
    """Call an OpenAI-compatible chat-completions endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        temperature: float,
        client_factory: Callable[[], httpx.Client] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.client_factory = client_factory or self._build_client

    def generate_reasoning(
        self,
        context: ReasoningContext,
        request: ReasoningRequest,
    ) -> ReasoningProviderResponse:
        """Generate grounded reasoning with retryable transport failures."""
        started = time.perf_counter()
        prompt_json = self._payload(context, request)
        try:
            with self.client_factory() as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=prompt_json,
                )
                response.raise_for_status()
                raw_text = response.text
                if len(raw_text.encode()) > settings.ai_max_response_bytes:
                    raise ReasoningTransientProviderError(
                        "Reasoning response exceeded configured size limit"
                    )
                payload = response.json()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ReasoningTransientProviderError(str(exc)) from exc
        except httpx.HTTPStatusError as exc:
            raise ReasoningTransientProviderError(str(exc)) from exc
        except json.JSONDecodeError as exc:
            raise ReasoningTransientProviderError(str(exc)) from exc

        content = self._extract_content(payload)
        structured = self._parse_structured_json(content)
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ReasoningProviderResponse(
            provider=request.model_provider,
            model=request.model_name,
            raw_json=structured,
            latency_ms=latency_ms,
            input_tokens=self._usage_value(usage, "prompt_tokens"),
            output_tokens=self._usage_value(usage, "completion_tokens"),
            total_tokens=self._usage_value(usage, "total_tokens"),
            estimated_cost=self._estimated_cost(usage),
        )

    def _build_client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout_seconds)

    def _payload(
        self, context: ReasoningContext, request: ReasoningRequest
    ) -> dict[str, object]:
        system_message = request.messages[0].content if request.messages else ""
        return {
            "model": request.model_name,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
            "metadata": {
                "prompt_version": request.prompt_version,
                "context_version": context.context_version,
                "reasoning_type": request.reasoning_type.value,
                "system_message": system_message,
            },
        }

    @staticmethod
    def _extract_content(payload: dict[str, object]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ReasoningTransientProviderError("Reasoning response missing choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ReasoningTransientProviderError("Reasoning response malformed")
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ReasoningTransientProviderError("Reasoning response missing message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ReasoningTransientProviderError("Reasoning response missing content")
        return content

    @staticmethod
    def _parse_structured_json(content: str) -> dict[str, object]:
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ReasoningTransientProviderError(
                "Reasoning response must be an object"
            )
        return parsed

    @staticmethod
    def _usage_value(usage: object, key: str) -> int | None:
        if not isinstance(usage, dict):
            return None
        value = usage.get(key)
        return int(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _estimated_cost(usage: object) -> float | None:
        if not isinstance(usage, dict):
            return None
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if not isinstance(prompt_tokens, (int, float)) or not isinstance(
            completion_tokens, (int, float)
        ):
            return None
        return round(
            (
                (float(prompt_tokens) / 1000.0)
                * settings.ai_estimated_cost_input_per_1k_tokens
            )
            + (
                (float(completion_tokens) / 1000.0)
                * settings.ai_estimated_cost_output_per_1k_tokens
            ),
            6,
        )
