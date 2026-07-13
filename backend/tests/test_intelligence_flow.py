"""End-to-end intelligence flow tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from backend.app.db.session import get_db
from backend.app.domain.trend_signal import TrendSignal
from backend.app.main import app
from backend.app.models.processed_event import ProcessedEventModel
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.evidence import EvidenceRepository
from backend.app.repositories.historical_evidence import (
    HistoricalEvidenceRepository,
)
from backend.app.repositories.processed_event import ProcessedEventRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.app.services.decision_engine import DecisionEngine
from backend.app.services.evidence_factory import EvidenceFactory
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.services.topic_normalization import TopicNormalizationService
from backend.app.utils.events import InMemoryDecisionEventEmitter, SignalDetected
from backend.app.workers import tasks as worker_tasks


class _FakePostgresConnection:
    def __enter__(self) -> _FakePostgresConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        return None

    def execute(self, statement: Any) -> None:
        return None


class _FakePostgresEngine:
    def connect(self) -> _FakePostgresConnection:
        return _FakePostgresConnection()

    def dispose(self) -> None:
        return None


class _HealthyRedis:
    @classmethod
    def from_url(cls, url: str) -> _HealthyRedis:
        return cls()

    def ping(self) -> bool:
        return True


class _UnhealthyRedis(_HealthyRedis):
    def ping(self) -> bool:
        raise RuntimeError("redis unavailable")


def _signal_event(
    *,
    event_id: str,
    correlation_id: str,
    topic_name: str,
    score: float = 1.0,
    confidence: float = 1.0,
) -> SignalDetected:
    return SignalDetected(
        event_id=event_id,
        correlation_id=correlation_id,
        signal=TrendSignal(
            source="google_trends",
            score=score,
            confidence=confidence,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            reason=(
                "Google Trends reported increasing search interest for "
                f"{topic_name} in US."
            ),
        ),
    )


def _override_session(session: Any) -> None:
    app.dependency_overrides[get_db] = lambda: session


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_topic_normalization_reuses_existing_topic(session: Any) -> None:
    repository = TopicRepository(session)
    service = TopicNormalizationService(repository)

    topic_one = service.resolve("  Ancient   Egypt  ")
    topic_two = service.resolve("ANCIENT egypt")

    assert topic_one.id == topic_two.id
    assert topic_one.display_name == "Ancient Egypt"
    assert topic_one.normalized_key == "ancient egypt"


def test_signal_to_evidence_mapping_uses_neutral_defaults(session: Any) -> None:
    topic = TopicRepository(session).create("Ancient Egypt", "ancient egypt")
    content = EvidenceFactory().build_content(
        topic,
        TrendSignal(
            source="google_trends",
            score=1.0,
            confidence=1.0,
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            reason=(
                "Google Trends reported increasing search interest for "
                "Ancient Egypt."
            ),
        ),
        signal_id="signal-1",
        correlation_id="correlation-1",
        event_version="v1",
    )

    decision = DecisionEngine().evaluate(content, content.signals)

    competition = next(
        evidence for evidence in decision.evidence if evidence.factor == "Competition"
    )
    assert competition.normalized_value == 0.5
    assert competition.contribution == 5.0
    assert decision.weights_snapshot["competition"] == 0.10


def test_signal_decision_service_persists_traceable_decision(session: Any) -> None:
    emitter = InMemoryDecisionEventEmitter()
    service = SignalDecisionService(session, event_emitter=emitter)
    event = _signal_event(
        event_id="event-1",
        correlation_id="correlation-1",
        topic_name="Ancient Egypt",
    )

    result = service.process(event)

    assert result.decision.topic_name == "Ancient Egypt"
    assert result.decision.engine_version == "v1"
    assert result.decision.event_version == "v1"
    assert result.decision.correlation_id == "correlation-1"
    assert result.processed_event.event_id == "event-1"
    assert len(result.evidence) == 7
    assert len(result.decision.explanations) == 7
    assert len(emitter.events) == 1
    assert emitter.events[0].decision_id == result.decision.id
    assert len(TopicRepository(session).list(10, 0)) == 1
    assert len(TrendSignalRepository(session).list(10, 0)) == 1
    assert len(DecisionRepository(session).list(10, 0)) == 1
    assert ProcessedEventRepository(session).exists("event-1") is True

    evidence_ids = {
        evidence.id
        for evidence in EvidenceRepository(session).list_by_decision(result.decision.id)
    }
    historical_evidence = HistoricalEvidenceRepository(session).list_by_topic(
        result.topic.id
    )
    assert historical_evidence
    assert {record.evidence_id for record in historical_evidence} == evidence_ids


def test_signal_decision_service_is_idempotent_for_duplicate_event(
    session: Any,
) -> None:
    service = SignalDecisionService(session)
    event = _signal_event(
        event_id="event-duplicate",
        correlation_id="correlation-dup",
        topic_name="Ancient Egypt",
    )

    first = service.process(event)
    second = service.process(event)

    assert first.decision.id == second.decision.id
    assert second.duplicate is True
    assert len(DecisionRepository(session).list(10, 0)) == 1


def test_signal_decision_service_rolls_back_on_failure(session: Any) -> None:
    service = SignalDecisionService(session)
    event = _signal_event(
        event_id="event-rollback",
        correlation_id="correlation-rollback",
        topic_name="Ancient Egypt",
    )

    def fail(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    service.decision_explanation_repository.create = fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="boom"):
        service.process(event)

    assert len(TopicRepository(session).list(10, 0)) == 0
    assert len(TrendSignalRepository(session).list(10, 0)) == 0
    assert len(DecisionRepository(session).list(10, 0)) == 0
    assert session.query(ProcessedEventModel).count() == 0


def test_decision_calculated_emitted_only_after_commit(session: Any) -> None:
    emitter = InMemoryDecisionEventEmitter()
    service = SignalDecisionService(session, event_emitter=emitter)
    event = _signal_event(
        event_id="event-no-emit",
        correlation_id="correlation-no-emit",
        topic_name="Ancient Egypt",
    )

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("commit failed")

    service.processed_event_repository.create_processed_record = fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="commit failed"):
        service.process(event)

    assert emitter.events == []


def test_api_endpoints_return_persisted_data(session: Any) -> None:
    service = SignalDecisionService(session)
    first_event = _signal_event(
        event_id="event-api-1",
        correlation_id="correlation-api-1",
        topic_name="Ancient Egypt",
    )
    second_event = _signal_event(
        event_id="event-api-2",
        correlation_id="correlation-api-2",
        topic_name="AI Video Tools",
    )
    first_result = service.process(first_event)
    service.process(second_event)

    _override_session(session)
    try:
        with TestClient(app) as client:
            signals_response = client.get("/api/v1/signals")
            assert signals_response.status_code == 200
            assert len(signals_response.json()) == 2
            assert signals_response.json()[0]["unified_signal"]["signal_type"] == (
                "SEARCH_TREND"
            )

            signal_detail = client.get(f"/api/v1/signals/{first_result.signal.id}")
            assert signal_detail.status_code == 200
            assert signal_detail.json()["topic_name"] == "Ancient Egypt"
            assert signal_detail.json()["unified_signal"]["topic_id"] == (
                first_result.topic.id
            )

            decisions_response = client.get("/api/v1/decisions")
            assert decisions_response.status_code == 200
            assert len(decisions_response.json()) == 2

            decision_detail = client.get(
                f"/api/v1/decisions/{first_result.decision.id}"
            )
            assert decision_detail.status_code == 200
            assert decision_detail.json()["evidence"]

            topic_response = client.get("/api/v1/topics")
            assert topic_response.status_code == 200
            assert len(topic_response.json()) == 2

            topic_detail = client.get(f"/api/v1/topics/{first_result.topic.id}")
            assert topic_detail.status_code == 200
            assert topic_detail.json()["normalized_key"] == "ancient egypt"

            topic_decisions = client.get(
                f"/api/v1/topics/{first_result.topic.id}/decisions"
            )
            assert topic_decisions.status_code == 200
            assert len(topic_decisions.json()) == 1

            paginated = client.get("/api/v1/decisions?limit=1&offset=1")
            assert paginated.status_code == 200
            assert len(paginated.json()) == 1

            empty_page = client.get("/api/v1/decisions?limit=1&offset=99")
            assert empty_page.status_code == 200
            assert empty_page.json() == []

            assert client.get("/api/v1/decisions/missing").status_code == 404
            assert client.get("/api/v1/signals/missing").status_code == 404
            assert client.get("/api/v1/topics/missing").status_code == 404
    finally:
        _clear_overrides()


def test_readiness_endpoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.readiness.create_engine",
        lambda *args, **kwargs: _FakePostgresEngine(),
    )
    monkeypatch.setattr("backend.app.services.readiness.Redis", _HealthyRedis)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "postgres": "ok", "redis": "ok"}


def test_readiness_endpoint_postgres_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _BrokenEngine(_FakePostgresEngine):
        def connect(self) -> _FakePostgresConnection:
            raise OperationalError("SELECT 1", {}, RuntimeError("postgres unavailable"))

    monkeypatch.setattr(
        "backend.app.services.readiness.create_engine",
        lambda *args, **kwargs: _BrokenEngine(),
    )
    monkeypatch.setattr("backend.app.services.readiness.Redis", _HealthyRedis)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "postgres": "error",
        "redis": "ok",
    }


def test_readiness_endpoint_redis_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.services.readiness.create_engine",
        lambda *args, **kwargs: _FakePostgresEngine(),
    )
    monkeypatch.setattr("backend.app.services.readiness.Redis", _UnhealthyRedis)

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "postgres": "ok",
        "redis": "error",
    }


def test_process_signal_detected_task_retries_on_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_process(self: Any, event: SignalDetected) -> Any:
        raise OperationalError("stmt", {}, RuntimeError("transient"))

    def fail_retry(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("retry requested")

    monkeypatch.setattr(
        "backend.app.services.signal_decision.SignalDecisionService.process",
        fail_process,
    )
    monkeypatch.setattr(worker_tasks.process_signal_detected, "retry", fail_retry)

    with pytest.raises(RuntimeError, match="retry requested"):
        worker_tasks.process_signal_detected.run(
            _signal_event(
                event_id="task-retry",
                correlation_id="task-retry",
                topic_name="Ancient Egypt",
            ).to_payload()
        )


def test_process_signal_detected_task_rejects_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_process(self: Any, event: SignalDetected) -> Any:
        raise ValueError("invalid payload")

    monkeypatch.setattr(
        "backend.app.services.signal_decision.SignalDecisionService.process",
        fail_process,
    )

    result = worker_tasks.process_signal_detected.run(
        _signal_event(
            event_id="task-validation",
            correlation_id="task-validation",
            topic_name="Ancient Egypt",
        ).to_payload()
    )

    assert result == {
        "status": "validation_failed",
        "event_id": "task-validation",
    }


def test_poll_google_trends_skips_malformed_items_and_emits_one_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports: list[dict[str, Any]] = []

    def fake_run(self: Any, connector_kwargs: Any, *, enabled_connectors: Any) -> Any:
        reports.append(
            {
                "connector_kwargs": connector_kwargs,
                "enabled_connectors": enabled_connectors,
            }
        )

        class _Report:
            started_at = datetime(2026, 1, 1, tzinfo=UTC)
            completed_at = datetime(2026, 1, 1, tzinfo=UTC)
            duration_ms = 1
            connector_reports = ()

        return _Report()

    monkeypatch.setattr(
        "backend.app.services.connector_orchestrator.ConnectorOrchestrator.run",
        fake_run,
    )

    result = worker_tasks.poll_google_trends.run(geo="US", limit=3)

    assert reports == [
        {
            "connector_kwargs": {"google_trends": {"geo": "US", "limit": 3}},
            "enabled_connectors": ("google_trends",),
        }
    ]
    assert result["duration_ms"] == 1
