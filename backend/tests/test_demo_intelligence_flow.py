"""Tests for the fixture-backed intelligence flow demo script."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.db.base import Base
from backend.app.models.processed_event import ProcessedEventModel
from backend.app.repositories.decision import DecisionRepository
from backend.app.repositories.topic import TopicRepository
from backend.app.repositories.trend_signal import TrendSignalRepository
from backend.scripts import demo_intelligence_flow as demo


def test_configured_mode_uses_application_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, dispose = _sqlite_session_factory()
    calls = {"count": 0}

    def tracked_factory():
        calls["count"] += 1
        return factory()

    monkeypatch.setattr(demo, "SessionLocal", tracked_factory)
    monkeypatch.setattr(
        demo.settings,
        "database_url",
        "postgresql+psycopg://viralforge:secret@postgres:5432/viralforge",
    )

    try:
        result = demo.run_demo(database_mode="configured")
        assert result.persisted is True
        assert calls["count"] >= 2
        assert "postgresql+psycopg://viralforge:***@postgres:5432/viralforge" in (
            result.database_url
        )
    finally:
        dispose()


def test_main_prints_redacted_database_url_and_persisted_true(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    factory, dispose = _sqlite_session_factory()
    monkeypatch.setattr(demo, "SessionLocal", factory)
    monkeypatch.setattr(
        demo.settings,
        "database_url",
        "postgresql+psycopg://viralforge:secret@postgres:5432/viralforge",
    )

    try:
        exit_code = demo.main([])
        captured = capsys.readouterr().out
        assert exit_code == 0
        assert (
            "database_url=postgresql+psycopg://viralforge:***@postgres:5432/viralforge"
            in (captured)
        )
        assert "decision_id=" in captured
        assert "decision_score=" in captured
        assert "persisted=true" in captured
    finally:
        dispose()


def test_configured_mode_commits_and_decision_can_be_read_back() -> None:
    factory, dispose = _sqlite_session_factory()

    try:
        result = demo.run_demo(database_mode="configured", session_factory=factory)
        with factory() as session:
            decision = DecisionRepository(session).get_by_id(result.decision_id)
            assert decision is not None
            assert decision.score == result.decision_score
    finally:
        dispose()


def test_isolated_mode_uses_sqlite_and_avoids_application_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_factory() -> None:
        raise AssertionError("configured application session factory should not run")

    monkeypatch.setattr(demo, "SessionLocal", fail_factory)

    result = demo.run_demo(database_mode="isolated", stable_event_id=True)

    assert result.database_url == "sqlite+pysqlite:///:memory:"
    assert result.persisted is True


def test_stable_event_id_remains_idempotent() -> None:
    factory, dispose = _sqlite_session_factory()

    try:
        first = demo.run_demo(
            database_mode="configured",
            stable_event_id=True,
            session_factory=factory,
        )
        second = demo.run_demo(
            database_mode="configured",
            stable_event_id=True,
            session_factory=factory,
        )

        assert first.decision_id == second.decision_id
        with factory() as session:
            assert len(DecisionRepository(session).list(10, 0)) == 1
    finally:
        dispose()


def test_failure_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    factory, dispose = _sqlite_session_factory()

    def fail_create(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "backend.app.repositories.decision.DecisionRepository.create", fail_create
    )

    try:
        with pytest.raises(RuntimeError, match="boom"):
            demo.run_demo(database_mode="configured", session_factory=factory)

        with factory() as session:
            assert len(TopicRepository(session).list(10, 0)) == 0
            assert len(TrendSignalRepository(session).list(10, 0)) == 0
            assert len(DecisionRepository(session).list(10, 0)) == 0
            assert session.query(ProcessedEventModel).count() == 0
    finally:
        dispose()


def _sqlite_session_factory() -> tuple[Callable[[], object], Callable[[], None]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def dispose() -> None:
        with suppress(Exception):
            engine.dispose()

    return factory, dispose
