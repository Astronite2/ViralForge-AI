"""Runtime connector health storage backed by Redis with local fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

from redis import Redis
from redis.exceptions import RedisError

from backend.app.connectors.metadata import ConnectorMetadata
from backend.app.core.config import settings
from backend.app.domain.connector_orchestration import ConnectorExecutionReport


@dataclass(frozen=True, slots=True)
class ConnectorRuntimeStatus:
    """Current connector state exposed to operational consumers."""

    connector_name: str
    status: str
    enabled: bool
    provider: str | None
    provider_experimental: bool
    last_run_at: datetime | None
    last_success_at: datetime | None
    error_code: str | None
    message: str | None


class ConnectorStatusStore:
    """Persist latest execution status without changing the SQL schema."""

    _memory: ClassVar[dict[str, dict[str, Any]]] = {}
    _key_prefix = "viralforge:connector-status:"

    def __init__(self, *, use_redis: bool = True) -> None:
        self.use_redis = use_redis

    @classmethod
    def clear_local(cls) -> None:
        """Clear process-local status state, primarily for isolated tests."""
        cls._memory.clear()

    def record(
        self, report: ConnectorExecutionReport, *, completed_at: datetime
    ) -> None:
        """Record the latest run while retaining the last successful run time."""
        previous = self._read_payload(report.connector_name) or {}
        last_success_at = previous.get("last_success_at")
        if report.status == "success" and report.items_processed > 0:
            last_success_at = completed_at.isoformat()
        payload = {
            "connector_name": report.connector_name,
            "run_status": report.status,
            "provider": report.provider,
            "provider_experimental": report.provider_experimental,
            "last_run_at": completed_at.isoformat(),
            "last_success_at": last_success_at,
            "error_code": report.error_code,
            "message": report.errors[0] if report.errors else None,
            "items_processed": report.items_processed,
        }
        self._memory[report.connector_name] = payload
        if not self.use_redis:
            return
        try:
            self._redis().set(
                f"{self._key_prefix}{report.connector_name}",
                json.dumps(payload, separators=(",", ":")),
            )
        except (RedisError, OSError):
            return

    def list_statuses(
        self, metadata: tuple[ConnectorMetadata, ...] | None = None
    ) -> tuple[ConnectorRuntimeStatus, ...]:
        """Return configured connector states with freshness applied."""
        if metadata is None:
            from backend.app.connectors.registry import build_default_connector_registry

            metadata = build_default_connector_registry(
                include_disabled=True
            ).list_metadata()
        return tuple(
            self._status(
                item.name,
                item.provider != "disabled",
                item.provider,
                item.provider_experimental,
            )
            for item in metadata
        )

    def _status(
        self, name: str, enabled: bool, provider: str, experimental: bool
    ) -> ConnectorRuntimeStatus:
        payload = self._read_payload(name) or {}
        last_run_at = _datetime(payload.get("last_run_at"))
        last_success_at = _datetime(payload.get("last_success_at"))
        if not enabled:
            status = "disabled"
            message = "Connector is disabled by configuration."
            error_code = "disabled"
        else:
            run_status = str(payload.get("run_status", "unobserved"))
            status = self._public_status(
                run_status,
                int(payload.get("items_processed", 0)),
                last_run_at,
            )
            message_value = payload.get("message")
            message = str(message_value) if message_value else None
            error_value = payload.get("error_code")
            error_code = str(error_value) if error_value else None
        return ConnectorRuntimeStatus(
            connector_name=name,
            status=status,
            enabled=enabled,
            provider=str(payload.get("provider") or provider),
            provider_experimental=bool(
                payload.get("provider_experimental", experimental)
            ),
            last_run_at=last_run_at,
            last_success_at=last_success_at,
            error_code=error_code,
            message=message,
        )

    @staticmethod
    def _public_status(
        run_status: str, items_processed: int, last_run_at: datetime | None
    ) -> str:
        if run_status in {"degraded", "unavailable", "disabled"}:
            return run_status
        if run_status == "failed":
            return "degraded"
        if run_status == "success" and items_processed > 0 and last_run_at is not None:
            active_window = timedelta(
                minutes=settings.connector_status_active_window_minutes
            )
            if datetime.now(UTC) - last_run_at <= active_window:
                return "active"
        return "unobserved"

    def _read_payload(self, name: str) -> dict[str, Any] | None:
        if self.use_redis:
            try:
                value = self._redis().get(f"{self._key_prefix}{name}")
                if isinstance(value, str):
                    parsed = json.loads(value)
                    if isinstance(parsed, dict):
                        self._memory[name] = parsed
                        return parsed
            except (RedisError, OSError, json.JSONDecodeError):
                pass
        return self._memory.get(name)

    @staticmethod
    def _redis() -> Redis:
        return Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
        )


def _datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
