# Connector SDK

The platform now uses Connector SDK v2 metadata and typed capability discovery.
See [Connector SDK v2](connector-sdk-v2.md) for the contract, current declarations,
API, and extension guide. The v1 processing interface remains backward compatible.

The Connector SDK v1 provides a pluggable boundary for platform integrations without
allowing platform-specific logic to leak into services, repositories, or routes.

## Architecture

- `BaseConnector` defines the contract: `fetch()`, `validate()`, and `normalize()`.
- `ConnectorRegistry` stores connector instances by name.
- `ConnectorPollingService` orchestrates polling, normalization, and event emission.
- `UnifiedSignalNormalizer` converts normalized connector output into the common
  intelligence schema before decision processing.
- `SignalDetected` is emitted when a connector normalizes a `TrendSignal`.
- `ContentPipeline.process_normalized()` accepts already-normalized content objects
  from content connectors and runs the existing enrichment, analysis, opportunity,
  and persistence stages.

## Google Trends Connector

The connector is transport-independent. `GoogleTrendsProvider` defines
`fetch_trending`, `interest_over_time`, `related_queries`, and `related_topics`;
the existing `GoogleTrendsConnector` remains responsible for validation and
`TrendSignal` normalization.

Available providers:

- `OfficialGoogleTrendsProvider`: configuration-driven typed stub. It reports
  `configuration_required` until approved alpha access and all official settings
  are supplied. It does not guess an endpoint or pretend that access works.
- `PytrendsGoogleTrendsProvider`: explicitly experimental fallback. Pytrends is
  unofficial and can break whenever Google changes its internal endpoints.
- `FixtureGoogleTrendsProvider`: deterministic tests only. Application
  configuration explicitly rejects selecting it.
- `DisabledGoogleTrendsProvider`: selected when `GOOGLE_TRENDS_ENABLED=false`.

- Supports daily trending searches, interest over time, related queries, and
  related topics.
- Accepts geographic, timeframe, category, language, and result-limit filters.
- Validates provider-neutral results before normalization.
- Normalizes each item into a platform-independent `TrendSignal`.
- Generates deterministic signal IDs and includes source/filter metadata.
- Retries rate limits and temporary failures with bounded exponential backoff.
- Converts pytrends HTTP 404 responses directly to `provider_unavailable` without
  retrying the permanent failure.
- Emits a `SignalDetected` event for downstream consumers.

The default trend type is `daily_trending_searches`. The other supported values
require `query` (or its `keyword` alias): `interest_over_time`,
`related_queries`, and `related_topics`.

Configuration is environment-based:

- `GOOGLE_TRENDS_ENABLED` (default `true`)
- `GOOGLE_TRENDS_PROVIDER` (`pytrends` or `official`; default `pytrends`)
- `GOOGLE_TRENDS_DEFAULT_GEO` (default `US`)
- `GOOGLE_TRENDS_DEFAULT_TIMEFRAME` (default `today 7-d`)
- `GOOGLE_TRENDS_MAX_RESULTS` (default `10`)
- `GOOGLE_TRENDS_RETRIES` (default `2`)
- `GOOGLE_TRENDS_BACKOFF_SECONDS` (default `1`)

Official-provider placeholders are empty by default:

- `GOOGLE_TRENDS_OFFICIAL_PROJECT_ID`
- `GOOGLE_TRENDS_OFFICIAL_CREDENTIALS_FILE`
- `GOOGLE_TRENDS_OFFICIAL_API_ENDPOINT`
- `GOOGLE_TRENDS_OFFICIAL_ACCESS_ENABLED`

Google currently describes the official API as a limited alpha. Apply through
the [official Google Trends API alpha page](https://developers.google.com/search/apis/trends).
After acceptance, use only the endpoint, project, credentials, and access
instructions supplied in the restricted official documentation. Until an
approved-access client is implemented, the official provider remains a safe
typed stub.

## Runtime connector status

The orchestrator records its latest connector report in Redis. The read-only
`GET /api/v1/connectors/status` endpoint exposes:

- `active`: the latest run processed data within the configured freshness window
- `degraded`: the latest run hit a transient failure or rate limit
- `unavailable`: the selected provider is permanently unavailable or needs access
  configuration
- `disabled`: connector intentionally disabled
- `unobserved`: configured, but no recent successful run

The latest run always controls the state. A current 404 therefore remains
`unavailable` even when older Google Trends observations exist. Provider failures
never generate placeholder signals or fabricated trend data.

## Scheduled Polling

Celery beat schedules `backend.app.workers.tasks.poll_google_trends` every five
minutes. The task uses the default connector registry and returns a JSON-safe summary.

## Extending the SDK

1. Implement a new `BaseConnector` subclass.
2. Register it in `ConnectorRegistry`.
3. Populate real dimensions in `TrendSignal.metadata` or embedded `Content`
   metrics; leave unavailable values absent.
4. Add a polling task or schedule entry if the connector should run periodically.
5. Route normalized `Content` or `TrendSignal` through `ConnectorOrchestrator`.

See [Unified Signal Engine](unified-signal-engine.md) for the schema and future
connector mapping rules.

## Testing Strategy

- Registry resolution
- pytrends response normalization and metadata
- empty, retry, rate-limit, and bad-request behavior
- deterministic signal IDs
- Polling orchestration
- Signal event emission
- Content pipeline integration for pre-normalized content
