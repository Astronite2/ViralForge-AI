"""AI reasoning engine tests."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

import backend.app.services.reasoning as reasoning_service_module
from backend.app.core.config import settings
from backend.app.dependencies.database import get_db
from backend.app.domain.reasoning import (
    ReasoningContext,
    ReasoningProviderResponse,
    ReasoningRequest,
    ReasoningStatus,
    ReasoningType,
)
from backend.app.domain.trend_signal import TrendSignal
from backend.app.main import app
from backend.app.reasoning.errors import (
    ReasoningDisabledError,
    ReasoningTransientProviderError,
    ReasoningValidationError,
)
from backend.app.reasoning.providers.openai_compatible import (
    OpenAICompatibleReasoningProvider,
)
from backend.app.repositories.reasoning import ReasoningRunRepository
from backend.app.services.reasoning import ReasoningService
from backend.app.services.reasoning_context import ReasoningContextBuilder
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.utils.events import (
    InMemoryReasoningEventEmitter,
    ReasoningCompleted,
    ReasoningValidationFailed,
    SignalDetected,
)
from backend.app.workers import tasks as worker_tasks


class _FakeReasoningProvider:
    def __init__(
        self,
        *,
        invalid_source: bool = False,
        transient_error: Exception | None = None,
    ) -> None:
        self.invalid_source = invalid_source
        self.transient_error = transient_error
        self.calls = 0

    def generate_reasoning(
        self,
        context: ReasoningContext,
        request: Any,
    ) -> ReasoningProviderResponse:
        if self.transient_error is not None:
            self.calls += 1
            raise self.transient_error
        self.calls += 1
        payload = self._payload(context, request)
        if self.invalid_source:
            payload["source_references"] = [
                {
                    "evidence_id": "missing-evidence",
                    "source": "google_trends",
                    "factor": "Trend Momentum",
                    "claim": "Invented evidence",
                    "contribution": 0.0,
                    "confidence": 0.0,
                }
            ]
        return ReasoningProviderResponse(
            provider=request.model_provider,
            model=request.model_name,
            raw_json=payload,
            latency_ms=1,
            input_tokens=120,
            output_tokens=60,
            total_tokens=180,
            estimated_cost=0.0,
        )

    def _payload(self, context: ReasoningContext, request: Any) -> dict[str, object]:
        decision = context.facts.get("decision", {})
        evidence = [asdict(reference) for reference in context.evidence]
        if request.reasoning_type == ReasoningType.OPPORTUNITY_COMPARISON:
            alternative_topics: list[dict[str, object]] = []
            for snapshot in context.facts.get("topic_snapshots", []):
                if not isinstance(snapshot, dict):
                    continue
                topic = snapshot.get("topic", {})
                scores = snapshot.get("scores", {})
                if not isinstance(topic, dict) or not isinstance(scores, dict):
                    continue
                opportunity_scores = scores.get("opportunity", {})
                decision_scores = scores.get("decision", {})
                alternative_topics.append(
                    {
                        "topic_id": topic.get("id"),
                        "topic_name": topic.get("display_name"),
                        "opportunity_score": float(
                            opportunity_scores.get("score", 0.0)
                        ),
                        "decision_score": float(decision_scores.get("score", 0.0)),
                        "relative_strengths": ["grounded evidence"],
                        "relative_weaknesses": ["limited scope"],
                        "comparison_summary": (
                            "Grounded comparison derived from stored scores."
                        ),
                    }
                )
        else:
            alternative_topics = []
        return {
            "executive_summary": "Grounded reasoning summary.",
            "why_now": "Persisted evidence supports acting now.",
            "why_this_topic": str(context.topic.get("display_name", "")),
            "why_this_platform": (
                "This reasoning is grounded in persisted evidence and metadata."
            ),
            "what_changed": "A deterministic decision already exists for this topic.",
            "supporting_evidence": evidence,
            "conflicting_evidence": evidence if context.contradictions else [],
            "caveats": list(context.missing_data),
            "confidence_assessment": (
                "Confidence remains aligned with the deterministic decision."
            ),
            "recommended_execution": {
                "recommended_action": decision.get("recommended_action", "review"),
                "caveat": "Grounded suggestion only.",
            },
            "alternative_topics": alternative_topics,
            "source_references": evidence,
        }


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, Any], *, text: str | None = None) -> None:
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHTTPClient:
    def __init__(self, response: _FakeHTTPResponse | Exception) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def __enter__(self) -> _FakeHTTPClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        return None

    def post(self, url: str, **kwargs: Any) -> _FakeHTTPResponse:
        self.requests.append({"url": url, **kwargs})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _seed_decision(session: Any, topic_name: str, event_id: str) -> Any:
    event = SignalDetected(
        event_id=event_id,
        correlation_id=f"corr-{event_id}",
        signal=TrendSignal(
            source="google_trends",
            score=1.0,
            confidence=1.0,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            reason=(
                "Google Trends reported increasing search interest for "
                f"{topic_name}."
            ),
        ),
    )
    return SignalDecisionService(session).process(event).decision


def _enable_reasoning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_reasoning_enabled", True)
    monkeypatch.setattr(settings, "ai_model", "gpt-test")
    monkeypatch.setattr(settings, "ai_api_key", "test-key")
    monkeypatch.setattr(settings, "ai_provider", "openai")


def test_reasoning_context_builder_is_deterministic_and_traceable(
    session: Any,
) -> None:
    decision = _seed_decision(session, "Ancient Egypt", "ctx-1")
    builder = ReasoningContextBuilder(session)
    request = ReasoningRequest(
        reasoning_type=ReasoningType.DECISION_EXPLANATION,
        prompt_version=settings.ai_reasoning_prompt_version,
        context_version=settings.reasoning_context_version,
        model_provider="openai",
        model_name="gpt-test",
        messages=(),
        correlation_id="reasoning-corr",
        decision_id=decision.id,
        topic_id=decision.topic_id,
    )

    first = builder.build(request)
    second = builder.build(request)

    assert first == second
    assert first.context_version == settings.reasoning_context_version
    assert first.evidence
    assert first.traceability["decision_id"] == decision.id


def test_reasoning_service_caches_identical_request(
    session: Any, monkeypatch: Any
) -> None:
    _enable_reasoning(monkeypatch)
    decision = _seed_decision(session, "Ancient Egypt", "cache-1")
    provider = _FakeReasoningProvider()
    emitter = InMemoryReasoningEventEmitter()
    service = ReasoningService(session, provider=provider, event_emitter=emitter)

    first = service.explain_decision(decision.id)
    second = service.explain_decision(decision.id)

    assert provider.calls == 1
    assert first.result is not None
    assert second.result is not None
    assert first.result.id == second.result.id
    assert second.cached is True
    assert any(isinstance(event, ReasoningCompleted) for event in emitter.events)


def test_reasoning_service_comparison_grounds_alternative_topics(
    session: Any, monkeypatch: Any
) -> None:
    _enable_reasoning(monkeypatch)
    first_decision = _seed_decision(session, "Ancient Egypt", "cmp-1")
    second_decision = _seed_decision(session, "Cleopatra", "cmp-2")
    provider = _FakeReasoningProvider()
    service = ReasoningService(session, provider=provider)

    result = service.compare_opportunities(
        topic_ids=[first_decision.topic_id, second_decision.topic_id]
    )

    assert result.result is not None
    assert len(result.result.alternative_topics) == 2
    assert provider.calls == 1


def test_reasoning_service_validation_failure_persists(
    session: Any, monkeypatch: Any
) -> None:
    _enable_reasoning(monkeypatch)
    decision = _seed_decision(session, "Ancient Egypt", "validation-1")
    provider = _FakeReasoningProvider(invalid_source=True)
    emitter = InMemoryReasoningEventEmitter()
    service = ReasoningService(session, provider=provider, event_emitter=emitter)

    with pytest.raises(ReasoningValidationError):
        service.explain_decision(decision.id)

    runs = ReasoningRunRepository(session).list_by_decision(decision.id)
    assert runs[-1].status == ReasoningStatus.VALIDATION_FAILED.value
    assert any(isinstance(event, ReasoningValidationFailed) for event in emitter.events)


def test_reasoning_service_retries_transient_failure(
    session: Any, monkeypatch: Any
) -> None:
    _enable_reasoning(monkeypatch)
    monkeypatch.setattr(settings, "ai_max_retries", 1)
    decision = _seed_decision(session, "Ancient Egypt", "retry-1")
    provider = _FakeReasoningProvider(
        transient_error=ReasoningTransientProviderError("timeout")
    )
    service = ReasoningService(session, provider=provider)

    with pytest.raises(ReasoningTransientProviderError):
        service.explain_decision(decision.id)

    assert provider.calls == 2
    runs = ReasoningRunRepository(session).list_by_decision(decision.id)
    assert runs[0].status == ReasoningStatus.FAILED.value


def test_reasoning_service_disabled(session: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "ai_reasoning_enabled", False)
    decision = _seed_decision(session, "Ancient Egypt", "disabled-1")
    service = ReasoningService(session, provider=_FakeReasoningProvider())

    with pytest.raises(ReasoningDisabledError):
        service.explain_decision(decision.id)


def test_reasoning_api_success_and_retrieval(session: Any, monkeypatch: Any) -> None:
    _enable_reasoning(monkeypatch)
    decision = _seed_decision(session, "Ancient Egypt", "api-1")
    provider = _FakeReasoningProvider()

    monkeypatch.setattr(
        reasoning_service_module,
        "build_reasoning_provider",
        lambda: provider,
    )
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/reasoning/decision-explanation",
                json={"decision_id": decision.id, "force_refresh": True},
            )
            assert response.status_code == 200
            result = response.json()
            assert result["source_references"]

            result_response = client.get(f"/api/v1/reasoning/{result['id']}")
            assert result_response.status_code == 200
            assert result_response.json()["id"] == result["id"]

            decision_history = client.get(
                f"/api/v1/reasoning/by-decision/{decision.id}"
            )
            assert decision_history.status_code == 200
            assert decision_history.json()

            topic_history = client.get(
                f"/api/v1/reasoning/by-topic/{decision.topic_id}"
            )
            assert topic_history.status_code == 200
            assert topic_history.json()
    finally:
        app.dependency_overrides.clear()


def test_reasoning_api_disabled_returns_503(session: Any) -> None:
    decision = _seed_decision(session, "Ancient Egypt", "api-disabled")
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/reasoning/decision-explanation",
                json={"decision_id": decision.id, "force_refresh": False},
            )
            assert response.status_code == 503
            assert response.json()["status"] == "disabled"
    finally:
        app.dependency_overrides.clear()


def test_reasoning_provider_parses_structured_json() -> None:
    payload = {
        "choices": [{"message": {"content": json.dumps({"executive_summary": "ok"})}}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }
    client = _FakeHTTPClient(_FakeHTTPResponse(payload))
    provider = OpenAICompatibleReasoningProvider(
        api_key="key",
        base_url="https://example.test/v1",
        model="gpt-test",
        timeout_seconds=1.0,
        max_output_tokens=128,
        temperature=0.0,
        client_factory=lambda: client,  # type: ignore[return-value]
    )
    context = ReasoningContext(
        context_version="v1",
        reasoning_type=ReasoningType.DECISION_EXPLANATION,
        topic={"id": "topic-1", "display_name": "Topic"},
        facts={},
        scores={},
        evidence=(),
        uncertainty={},
    )
    request = ReasoningRequest(
        reasoning_type=ReasoningType.DECISION_EXPLANATION,
        prompt_version="v1",
        context_version="v1",
        model_provider="openai",
        model_name="gpt-test",
        messages=(),
        correlation_id="corr",
    )

    result = provider.generate_reasoning(context, request)

    assert result.raw_json["executive_summary"] == "ok"
    assert result.total_tokens == 15
    assert client.requests


def test_reasoning_provider_rejects_transient_failure() -> None:
    client = _FakeHTTPClient(httpx.TimeoutException("timeout"))
    provider = OpenAICompatibleReasoningProvider(
        api_key="key",
        base_url="https://example.test/v1",
        model="gpt-test",
        timeout_seconds=1.0,
        max_output_tokens=128,
        temperature=0.0,
        client_factory=lambda: client,  # type: ignore[return-value]
    )
    context = ReasoningContext(
        context_version="v1",
        reasoning_type=ReasoningType.DECISION_EXPLANATION,
        topic={"id": "topic-1", "display_name": "Topic"},
        facts={},
        scores={},
        evidence=(),
        uncertainty={},
    )
    request = ReasoningRequest(
        reasoning_type=ReasoningType.DECISION_EXPLANATION,
        prompt_version="v1",
        context_version="v1",
        model_provider="openai",
        model_name="gpt-test",
        messages=(),
        correlation_id="corr",
    )

    with pytest.raises(ReasoningTransientProviderError):
        provider.generate_reasoning(context, request)


def test_reasoning_task_delegates_to_service(session: Any, monkeypatch: Any) -> None:
    _enable_reasoning(monkeypatch)
    decision = _seed_decision(session, "Ancient Egypt", "task-1")

    class _FakeService:
        def __init__(self, db: Any) -> None:
            self.db = db

        def explain_decision(
            self, decision_id: str, *, force_refresh: bool = False
        ) -> Any:
            assert decision_id == decision.id
            assert force_refresh is True
            return type(
                "Result",
                (),
                {
                    "run": type("Run", (), {"id": "run-1"})(),
                    "result": type("Obj", (), {"id": "result-1"})(),
                    "cached": False,
                },
            )()

    monkeypatch.setattr(worker_tasks, "ReasoningService", _FakeService)

    payload = {
        "reasoning_type": ReasoningType.DECISION_EXPLANATION.value,
        "decision_id": decision.id,
        "force_refresh": True,
        "correlation_id": "corr",
    }

    result = worker_tasks.run_reasoning_request.run(payload)

    assert result["result_id"] == "result-1"
    assert result["run_id"] == "run-1"
