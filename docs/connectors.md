# Connector SDK

The Connector SDK v1 provides a pluggable boundary for platform integrations without
allowing platform-specific logic to leak into services, repositories, or routes.

## Architecture

- `BaseConnector` defines the contract: `fetch()`, `validate()`, and `normalize()`.
- `ConnectorRegistry` stores connector instances by name.
- `ConnectorPollingService` orchestrates polling, normalization, and event emission.
- `SignalDetected` is emitted when a connector normalizes a `TrendSignal`.
- `ContentPipeline.process_normalized()` accepts already-normalized content objects
  from content connectors and runs the existing enrichment, analysis, opportunity,
  and persistence stages.

## Google Trends Connector

The Google Trends connector uses the public RSS feed endpoint instead of HTML
scraping.

- Fetches RSS entries from `trendingsearches/daily/rss`.
- Validates the feed payload before normalization.
- Normalizes each item into a platform-independent `TrendSignal`.
- Emits a `SignalDetected` event for downstream consumers.

## Scheduled Polling

Celery beat schedules `backend.app.workers.tasks.poll_google_trends` every five
minutes. The task uses the default connector registry and returns a JSON-safe summary.

## Extending the SDK

1. Implement a new `BaseConnector` subclass.
2. Register it in `ConnectorRegistry`.
3. Add a polling task or schedule entry if the connector should run periodically.
4. Route normalized `Content` through `ContentPipeline.process_normalized()`.
5. Route normalized `TrendSignal` instances through the signal event path.

## Testing Strategy

- Registry resolution
- Google Trends normalization
- Polling orchestration
- Signal event emission
- Content pipeline integration for pre-normalized content
