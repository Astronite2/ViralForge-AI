# Intelligence Flow

## Architecture

The intelligence pipeline is deterministic and event driven:

1. Google Trends connector normalizes a platform signal.
2. A `SignalDetected` domain event is emitted.
3. `SignalDecisionService` resolves or creates the topic.
4. The signal is persisted.
5. `EvidenceFactory` maps the signal into factor inputs.
6. `DecisionEngine` produces a traceable decision.
7. Decision, evidence, explanations, and idempotency state are committed together.
8. `DecisionCalculated` is emitted only after the transaction commits.

## Event lifecycle

- `SignalDetected`
  - `event_id`
  - `signal`
  - `occurred_at`
  - `correlation_id`
  - `event_version`

- `DecisionCalculated`
  - `event_id`
  - `decision_id`
  - `topic_id`
  - `topic_name`
  - `score`
  - `confidence`
  - `occurred_at`
  - `correlation_id`
  - `engine_version`
  - `event_version`

Correlation IDs stay intact through the full processing chain.

## Topic normalization

`TopicNormalizationService`:

- trims leading and trailing whitespace
- collapses repeated internal whitespace
- lowercases the normalized lookup key
- reuses existing topics by normalized key
- avoids semantic merging or embeddings

Example:

- input: `"  Ancient   Egypt  "`
- display name: `"Ancient Egypt"`
- normalized key: `"ancient egypt"`

## Evidence mapping

Google Trends signals are mapped into:

- Trend Momentum
- Audience Demand
- Confidence

Neutral defaults come from configuration for:

- Revenue Potential
- Competition
- Evergreen
- Platform Fit

Every evidence record preserves:

- source
- factor
- raw_value
- normalized_value
- contribution
- confidence
- reason
- signal_id
- correlation_id

## Neutral defaults

Neutral values are configurable through `settings.neutral_factor_defaults`. They are not hardcoded in services.

## Decision evaluation

`DecisionEngine` uses configurable weighted scoring. The initial weights are loaded from `DecisionConfig` and stored in `weights_snapshot` on each decision.

## Transaction boundaries

`SignalDecisionService` commits in one database transaction:

- topic resolution
- signal persistence
- decision persistence
- evidence persistence
- explanation persistence
- processed-event persistence

If any part fails, the transaction rolls back.

## Idempotency

`ProcessedEvent.event_id` is unique. Reprocessing the same `SignalDetected.event_id` returns the existing persisted decision instead of creating duplicates.

## Retry policy

Celery task retries are controlled by configuration:

- retry limit
- retry delay
- polling batch size
- polling interval

Validation failures are not retried indefinitely.

## Failure isolation

Polling handles each connector item independently. One malformed trend does not block other signals in the batch.

## Persistence relationships

- Topic -> many TrendSignals
- Topic -> many Decisions
- TrendSignal -> many Evidence records
- Decision -> many Evidence records
- Decision -> many DecisionExplanation records

## API endpoints

- `GET /api/v1/signals`
- `GET /api/v1/signals/{signal_id}`
- `GET /api/v1/decisions`
- `GET /api/v1/decisions/{decision_id}`
- `GET /api/v1/topics`
- `GET /api/v1/topics/{topic_id}`
- `GET /api/v1/topics/{topic_id}/decisions`
- `GET /ready`
- `GET /health`

List endpoints support `limit` and `offset`.

## Readiness

`GET /ready` checks:

- PostgreSQL connectivity
- Redis connectivity

It returns `200` only when both are available and `503` otherwise.

## Demo flow

Run the local fixture-backed demo:

```bash
make demo-intelligence-flow
```

The command:

1. loads a fixture Google Trends item
2. validates and normalizes it
3. emits `SignalDetected`
4. processes the event
5. persists topic, signal, evidence, decision, explanations, and processed event
6. reads the decision back from the configured database
7. prints the database URL with credentials redacted
8. prints the resulting decision ID and score
9. prints `persisted=true`

The default CLI mode is `--database-mode configured`, which uses the application
`SessionLocal` and `settings.database_url`. For test isolation you can run:

```bash
python -m backend.scripts.demo_intelligence_flow --database-mode isolated
```

## Live polling

Enable the Google Trends polling beat schedule by configuring the environment and running the `beat` service from Docker Compose. The connector remains non-scraping and uses its normal fetch/normalize path.

## AI reasoning layer

The AI reasoning layer sits above the deterministic system and is disabled by
default. When enabled through configuration, it:

- builds a deterministic reasoning context from persisted topics, signals,
  evidence, history, opportunity scores, and decisions
- sends only structured, versioned context to the configured provider
- validates grounded structured JSON before persistence
- caches identical requests by stable input hash
- rejects unsupported or ungrounded output

Relevant endpoints:

- `POST /api/v1/reasoning/decision-explanation`
- `POST /api/v1/reasoning/opportunity-comparison`
- `POST /api/v1/reasoning/execution-strategy`
- `POST /api/v1/reasoning/change-summary`
- `GET /api/v1/reasoning/{reasoning_result_id}`
- `GET /api/v1/reasoning/by-decision/{decision_id}`
- `GET /api/v1/reasoning/by-topic/{topic_id}`

Configuration comes from the `AI_*` environment variables documented in
`.env.example`.
