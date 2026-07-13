"""Stable idempotency helpers for normalized signals and observations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal


def stable_signal_event_id(
    connector_name: str,
    normalized: TrendSignal | Content,
    *,
    signal_index: int = 0,
) -> str:
    """Create a deterministic event ID from normalized connector output."""
    canonical = _canonical_json(
        {
            "connector": connector_name,
            "signal_index": signal_index,
            "normalized": _normalized_payload(normalized),
        }
    )
    return str(uuid5(NAMESPACE_URL, canonical))


def stable_observation_hash(
    topic_id: str,
    source: str,
    normalized: TrendSignal,
    *,
    event_version: str,
    content: Mapping[str, object] | None = None,
) -> str:
    """Create a deterministic historical-observation hash from normalized state."""
    canonical = _canonical_json(
        {
            "topic_id": topic_id,
            "source": source,
            "event_version": event_version,
            "signal": _trend_signal_payload(normalized),
            "content": _json_safe(content) if content is not None else {},
        }
    )
    return uuid5(NAMESPACE_URL, canonical).hex


def _normalized_payload(normalized: TrendSignal | Content) -> dict[str, object]:
    if isinstance(normalized, TrendSignal):
        return _trend_signal_payload(normalized)
    return _content_payload(normalized)


def _trend_signal_payload(signal: TrendSignal) -> dict[str, object]:
    payload: dict[str, object] = {
        "source": signal.source,
        "score": signal.score,
        "confidence": signal.confidence,
        "timestamp": signal.timestamp.isoformat(),
        "reason": signal.reason,
    }
    metadata = getattr(signal, "metadata", None)
    if isinstance(metadata, Mapping) and metadata:
        payload["metadata"] = _json_safe(metadata)
    return payload


def _content_payload(content: Content) -> dict[str, object]:
    return {
        "id": content.id,
        "platform": content.platform,
        "creator_name": content.creator_name,
        "creator_id": content.creator_id,
        "title": content.title,
        "description": content.description,
        "url": content.url,
        "language": content.language,
        "country": content.country,
        "published_at": content.published_at.isoformat(),
        "duration_seconds": content.duration_seconds,
        "content_type": content.content_type,
        "metrics": _json_safe(content.metrics),
        "analysis": _json_safe(content.analysis),
        "signals": [_trend_signal_payload(signal) for signal in content.signals],
        "metadata": _json_safe(content.metadata),
    }


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def _json_safe(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    return value
