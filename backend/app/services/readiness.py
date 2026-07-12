"""Application readiness checks."""

from __future__ import annotations

from dataclasses import dataclass

from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings


@dataclass(frozen=True, slots=True)
class ReadinessStatus:
    """Structured readiness result."""

    postgres: str
    redis: str

    @property
    def status(self) -> str:
        return "ready" if self.postgres == "ok" and self.redis == "ok" else "not_ready"


class ReadinessService:
    """Check infrastructure dependencies without hitting external APIs."""

    def check(self) -> ReadinessStatus:
        postgres = self._check_postgres()
        redis = self._check_redis()
        return ReadinessStatus(postgres=postgres, redis=redis)

    def _check_postgres(self) -> str:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return "ok"
        except SQLAlchemyError:
            return "error"
        finally:
            engine.dispose()

    def _check_redis(self) -> str:
        try:
            client = Redis.from_url(settings.redis_url)
            client.ping()
            return "ok"
        except Exception:  # pragma: no cover - connection failure path
            return "error"
