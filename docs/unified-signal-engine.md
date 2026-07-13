# Unified Signal Engine

The Unified Signal Engine is the compatibility layer between connector output and
ViralForge's existing knowledge and decision pipeline.

```text
BaseConnector.fetch / validate / normalize
  -> TrendSignal or Content
  -> UnifiedSignalNormalizer
  -> UnifiedSignal
  -> SignalDecisionService
  -> Knowledge Layer / HistoricalObservation
  -> UnifiedEvidenceMapper
  -> existing Decision Engine factor contract
```

Connectors retain their existing public interface. The orchestrator persists
`Content` before passing a content-linked unified signal to
`SignalDecisionService`.

## Schema

`UnifiedSignal` is a frozen domain object. Every field is serialized explicitly;
unavailable optional values are `null`, never generated or silently replaced.

| Field | Type | Meaning |
| --- | --- | --- |
| `normalization_id` | string | UUID5 derived deterministically from normalized input and trace context |
| `topic_id`, `topic_name` | nullable string | Resolved topic identity; `topic_id` is filled after topic normalization |
| `source` | string | Connector/source name |
| `signal_type` | enum | Connector-neutral intelligence category |
| `observed_at` | timezone-aware datetime | Source observation time |
| `confidence` | number, 0–1 | Source confidence |
| `popularity`, `velocity`, `acceleration`, `engagement` | nullable number, 0–1 | Standardized performance dimensions |
| `sentiment`, `freshness`, `competition` | nullable number, 0–1 | Standardized qualitative/timing dimensions |
| `monetization`, `evergreen`, `platform_fit` | nullable number, 0–1 | Standardized opportunity dimensions |
| `geography`, `language` | nullable string | Source filters or content attributes |
| `raw_value` | nullable scalar | Original source measurement used by normalization |
| `normalized_value` | nullable number, 0–1 | Backward-compatible normalized score |
| `reason` | string | Human-readable source explanation |
| `evidence_references` | string list | Stable references to supporting source evidence |
| `connector_metadata` | object | Lossless connector trace metadata |
| `event_version`, `correlation_id` | string | Event trace context |
| `source_item_id` | nullable string | Native connector item identifier |
| `content_id` | nullable string | Persisted content foreign-key identity when applicable |

The representation is stored in `trend_signals.raw_metadata.unified_signal` and
in the historical observation JSON payload. No database migration is required.
`GET /api/v1/signals` exposes it as the optional `unified_signal` field while all
existing fields remain unchanged.

## Signal types

- `SEARCH_TREND`
- `CONTENT_PERFORMANCE`
- `DISCUSSION_VELOCITY`
- `NEWS_MOMENTUM`
- `AUDIENCE_DEMAND`
- `COMPETITION`
- `SENTIMENT`
- `PLATFORM_FIT`
- `MONETIZATION`
- `FRESHNESS`

## Current connector rules

### Google Trends

- Type: `SEARCH_TREND`
- `popularity`: existing normalized trend score
- `raw_value`: Google interest score
- geography/language/source item: connector metadata
- unsupported dimensions remain `null`

### YouTube

- Type: `CONTENT_PERFORMANCE`
- `popularity`: existing normalized content-performance score
- `engagement`: existing connector `engagement_rate`
- `raw_value`: view count
- geography/language/content/source item: normalized `Content`
- raw velocity, freshness hours, and channel-adjusted values remain in connector
  metadata; they are not treated as standardized dimensions until a documented
  0–1 normalization exists

### Legacy `TrendSignal`

Legacy objects remain accepted. Their existing `score` becomes `popularity` and
`normalized_value`; their other dimensions remain absent unless explicitly
provided in metadata. Google and YouTube source names select their known signal
type; other legacy sources default to `AUDIENCE_DEMAND` during migration.

## Evidence mapping

Mapping uses the first available standardized dimension in the documented order.
It does not average, infer, or synthesize missing dimensions.

| Existing factor | Unified dimension priority |
| --- | --- |
| Trend Momentum | `velocity`, `acceleration`, `popularity`, `freshness` |
| Audience Demand | `popularity`, `engagement`, `sentiment` |
| Revenue Potential | `monetization` |
| Competition | `competition` |
| Evergreen | `evergreen` |
| Platform Fit | `platform_fit`, `engagement` |
| Confidence | `confidence` |

Competition retains the Decision Engine's existing inverse normalization.
Sentiment below `0.5` is identified as conflicting evidence in the Audience Demand
reason; sentiment at or above `0.5` is identified as supporting evidence. It does
not silently modify another dimension's numeric value.

When no mapped dimension exists, the configured neutral value is used and the
evidence reason states that the unified dimension was absent. The decision input
also records `neutral_decision_factors`, `explicit_decision_factors`, and the full
`evidence_mapping` trace.

## Missing-data behavior

- `None` is preserved in the unified payload.
- The normalizer never derives sentiment, acceleration, monetization, evergreen,
  competition, freshness, or platform fit from unrelated values.
- Values outside the standardized 0–1 range are rejected with
  `MalformedSignalError`.
- Raw non-standard measurements remain in `raw_value` or connector metadata.
- Neutral factor defaults are applied only at the existing Decision Engine input
  boundary and are explicitly labeled.

## Adding Reddit next

1. Implement `RedditConnector(BaseConnector[Content])` or
   `BaseConnector[TrendSignal]`; keep fetch, validation, and source normalization
   inside the connector.
2. Produce deterministic native item IDs and timezone-aware observation times.
3. Set `source="reddit"` and
   `metadata["signal_type"]="DISCUSSION_VELOCITY"` on each embedded
   `TrendSignal`.
4. Populate only measurements Reddit actually provides. Recommended initial
   mappings are:
   - normalized post/comment growth -> `velocity`
   - normalized vote/comment interaction rate -> `engagement`
   - subreddit or locale -> `geography` only when the source provides it
   - post ID -> `source_item_id`
   - permalink -> `source_url` and/or `evidence_references`
5. Keep raw score, upvote ratio, comment count, subscriber count, and age in
   `connector_metadata`. Do not place raw unbounded counts in 0–1 dimensions.
6. Do not populate `sentiment` until a deterministic, tested sentiment source is
   intentionally added; this milestone does not infer it from Reddit text.
7. Register the connector in `ConnectorRegistry`. Do not add Reddit branches to
   `SignalDecisionService`, `DecisionEngine`, Knowledge Layer, or Celery business
   logic.
8. Route it through `ConnectorOrchestrator`; the existing normalizer reads the
   explicit signal type and dimensions.
9. Test empty data, malformed payloads, duplicate IDs, content-before-observation,
   standardized dimension ranges, evidence mapping, connector isolation, and a
   combined Google/YouTube/Reddit orchestration run with no network calls.
