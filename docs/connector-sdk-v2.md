# Connector SDK v2

Connector SDK v2 adds typed, read-only capability discovery without changing the
existing `fetch` → `validate` → `normalize` processing contract.

## Contract

Every `BaseConnector` exposes `metadata`, `capabilities`, `is_enabled`,
`availability`, and safe `diagnostics`, in addition to the v1 methods. Metadata
contains the connector identity and version, selected provider, experimental
flag, description, live/fixture support, and a deterministically ordered
`ConnectorCapabilities` set. Provider code owns transport and authentication;
the connector owns validation, normalization, and honest capability declaration.

The registry can list metadata, filter by a `ConnectorCapability`, and test
membership. The orchestrator copies metadata into reports and never branches on
connector or provider names. Runtime status remains an observation of the latest
execution, not a static capability.

## Current declarations

- Google Trends: `TRENDING`, `HISTORICAL`, `AUDIENCE_SIGNALS`, `GEO_FILTERING`,
  `DATE_FILTERING`, `TOPIC_MONITORING`, `FORECAST_INPUT`, `CONTENT_DISCOVERY`.
- YouTube: `SEARCH`, `CHANNELS`, `AUTHORS`, `ENGAGEMENT_METRICS`,
  `AUDIENCE_SIGNALS`, `GEO_FILTERING`, `KEYWORD_MONITORING`, `FORECAST_INPUT`,
  `CONTENT_DISCOVERY`.

YouTube does not declare `COMMENTS`: the connector reads a comment count but not
comment content. It does not declare `MONETIZATION_SIGNALS` because it exposes no
usable revenue evidence. Missing capabilities and empty sets are explicit.

## Discovery API

- `GET /api/v1/connectors` combines metadata with Redis-backed runtime status.
- `GET /api/v1/connectors?capability=SEARCH` filters by a typed capability.
- `GET /api/v1/connectors/capabilities` returns the stable platform catalog.
- `GET /api/v1/connectors/status` retains its v1 response.

Responses never contain API keys, credentials, provider client diagnostics, or
stack traces.

## Adding a future connector

1. Implement `BaseConnector` fetch, validation, and normalization methods.
2. Return immutable `ConnectorMetadata` and only capabilities demonstrated by
   normalized output or supported input filters.
3. Keep authentication and HTTP behavior in the provider/client boundary.
4. Register the connector; registry discovery and orchestration require no new
   connector-specific branches.
5. Add fixture-backed contract, normalization, isolation, and API tests.
6. Add polling explicitly; registration does not silently create a schedule.

This model allows future Reddit or News implementations to advertise communities,
authors, discussion velocity, or real-time behavior only after those features
exist. SDK v1 connectors remain functional through the base class defaults, but
should override metadata before being exposed as production integrations.
