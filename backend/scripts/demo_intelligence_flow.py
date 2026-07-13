"""Run the fixture-based intelligence flow end to end."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.connectors.google_trends import GoogleTrendsConnector
from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import SessionLocal
from backend.app.domain.trend_signal import TrendSignal
from backend.app.repositories.decision import DecisionRepository
from backend.app.services.signal_decision import SignalDecisionService
from backend.app.utils.events import InMemoryDecisionEventEmitter, SignalDetected
from backend.app.utils.idempotency import stable_signal_event_id


@dataclass(frozen=True, slots=True)
class DemoResult:
    """Structured result from the demo flow."""

    database_url: str
    decision_id: str
    decision_score: float
    persisted: bool


@dataclass(slots=True)
class DemoDatabase:
    """Resolved database/session configuration for the demo."""

    session_factory: Callable[[], Session]
    database_url: str
    dispose: Callable[[], None]


def main(argv: list[str] | None = None) -> int:
    """Execute the fixture-backed signal-to-decision flow."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-mode",
        choices=("configured", "isolated"),
        default="configured",
        help="Use the application database or a temporary SQLite database.",
    )
    parser.add_argument(
        "--stable-event-id",
        action="store_true",
        default=True,
        help="Use a deterministic event ID for idempotency testing.",
    )
    args = parser.parse_args(argv)

    try:
        result = run_demo(
            database_mode=args.database_mode,
            stable_event_id=args.stable_event_id,
        )
    except Exception as exc:  # pragma: no cover - CLI failure path
        print(f"error={exc}", file=sys.stderr)
        return 1

    print(f"database_url={result.database_url}")
    print(f"decision_id={result.decision_id}")
    print(f"decision_score={result.decision_score}")
    print("persisted=true")
    return 0


def run_demo(
    *,
    database_mode: str = "configured",
    stable_event_id: bool = True,
    session_factory: Callable[[], Session] | None = None,
    raw_item: dict[str, Any] | None = None,
) -> DemoResult:
    """Run the fixture-backed intelligence flow and verify persistence."""
    database = _build_database(database_mode, session_factory=session_factory)
    raw_item = raw_item or _fixture_google_trends_item()
    connector = GoogleTrendsConnector(fetcher=lambda geo, limit: [])
    connector.validate(raw_item)
    signal = connector.normalize(raw_item)
    event_id = _stable_event_id(signal) if stable_event_id else str(uuid4())
    correlation_id = (
        _stable_correlation_id(event_id) if stable_event_id else str(uuid4())
    )
    event = SignalDetected(
        signal=signal,
        correlation_id=correlation_id,
        event_id=event_id,
    )

    try:
        with database.session_factory() as session:
            emitter = InMemoryDecisionEventEmitter()
            result = SignalDecisionService(session, event_emitter=emitter).process(
                event
            )
            decision_id = result.decision.id
            decision_score = result.decision.score
            session.commit()

        with database.session_factory() as verification_session:
            persisted = DecisionRepository(verification_session).get_by_id(decision_id)
            if persisted is None:
                raise RuntimeError("Persisted decision could not be read back")

        return DemoResult(
            database_url=database.database_url,
            decision_id=decision_id,
            decision_score=decision_score,
            persisted=True,
        )
    finally:
        with suppress(Exception):
            database.dispose()


def _build_database(
    database_mode: str,
    *,
    session_factory: Callable[[], Session] | None = None,
) -> DemoDatabase:
    if database_mode == "configured":
        if session_factory is not None:
            return DemoDatabase(
                session_factory=session_factory,
                database_url=_redact_database_url(settings.database_url),
                dispose=lambda: None,
            )
        return DemoDatabase(
            session_factory=SessionLocal,
            database_url=_redact_database_url(settings.database_url),
            dispose=lambda: None,
        )

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return DemoDatabase(
        session_factory=factory,
        database_url="sqlite+pysqlite:///:memory:",
        dispose=engine.dispose,
    )


def _fixture_google_trends_item() -> dict[str, Any]:
    return {
        "query": "Ancient Egypt",
        "title": "Ancient Egypt",
        "url": "https://trends.google.com/trends/explore?q=Ancient%20Egypt",
        "published_at": datetime(2026, 1, 1, tzinfo=UTC),
        "rank": 1,
        "geo": "US",
    }


def _stable_event_id(signal: TrendSignal) -> str:
    return stable_signal_event_id("google_trends", signal)


def _stable_correlation_id(event_id: str) -> str:
    from uuid import NAMESPACE_URL, uuid5

    return str(uuid5(NAMESPACE_URL, f"{event_id}:correlation"))


def _redact_database_url(database_url: str) -> str:
    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except Exception:
        return database_url


if __name__ == "__main__":
    raise SystemExit(main())
