"""Connector polling orchestration."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.app.connectors.registry import ConnectorRegistry
from backend.app.domain.content import Content
from backend.app.domain.trend_signal import TrendSignal
from backend.app.pipeline.pipeline import ContentPipeline, PipelineResult
from backend.app.utils.events import SignalDetected, SignalEventEmitter


@dataclass(frozen=True, slots=True)
class ConnectorPollResult:
    """Results from polling one connector."""

    connector_name: str
    pipeline_results: tuple[PipelineResult, ...] = ()
    signals: tuple[TrendSignal, ...] = ()
    events: tuple[SignalDetected, ...] = ()


@dataclass(frozen=True, slots=True)
class PollSummary:
    """Results from polling all registered connectors."""

    results: tuple[ConnectorPollResult, ...] = field(default_factory=tuple)


class ConnectorPollingService:
    """Poll registered connectors and route normalized objects into the pipeline."""

    def __init__(
        self,
        registry: ConnectorRegistry,
        *,
        content_pipeline: ContentPipeline | None = None,
        event_emitter: SignalEventEmitter | None = None,
    ) -> None:
        self.registry = registry
        self.content_pipeline = content_pipeline or ContentPipeline()
        self.event_emitter = event_emitter

    def poll_connector(self, connector_name: str, **kwargs: Any) -> ConnectorPollResult:
        """Poll one connector and route normalized objects to the proper boundary."""
        connector = self.registry.get(connector_name)
        pipeline_results: list[PipelineResult] = []
        signals: list[TrendSignal] = []
        events: list[SignalDetected] = []

        for raw_item in connector.fetch(**kwargs):
            connector.validate(raw_item)
            normalized = connector.normalize(raw_item)
            if isinstance(normalized, Content):
                pipeline_result = self.content_pipeline.process_normalized(normalized)
                pipeline_results.append(pipeline_result)
                continue

            if isinstance(normalized, TrendSignal):
                event = SignalDetected(signal=normalized)
                signals.append(normalized)
                events.append(event)
                if self.event_emitter is not None:
                    self.event_emitter.emit(event)
                continue

            raise TypeError(
                "Connector normalization must return Content or TrendSignal"
            )

        return ConnectorPollResult(
            connector_name=connector_name,
            pipeline_results=tuple(pipeline_results),
            signals=tuple(signals),
            events=tuple(events),
        )

    def poll_all(
        self, connector_kwargs: Mapping[str, Mapping[str, Any]] | None = None
    ) -> PollSummary:
        """Poll every registered connector."""
        kwargs_by_connector = connector_kwargs or {}
        results = [
            self.poll_connector(name, **dict(kwargs_by_connector.get(name, {})))
            for name in self.registry.names()
        ]
        return PollSummary(results=tuple(results))
