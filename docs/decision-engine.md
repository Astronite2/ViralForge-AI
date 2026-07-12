# Decision Engine v1

## Architecture

The Decision Engine lives in the existing service layer. It consumes pure domain `Content` and `TrendSignal` objects and returns a pure `Decision`. API routes call `DecisionService`; they contain no scoring logic. The engine does not call external services, use machine learning, or persist data.

## Scoring flow

`DecisionEngine.evaluate()` reads weights from `DecisionConfig`, then evaluates Trend Momentum, Audience Demand, Revenue Potential, Competition, Evergreen, Platform Fit, and Confidence. Inputs are normalized to a `0.0–1.0` range. Each factor contribution is `normalized value × configured weight × 100`; the decision score is the sum of all contributions.

Competition is inverted after normalization, so less competition yields a higher contribution. Trend Momentum is derived from the supplied signals when present. Other factor values, confidence values, and optional reasons are read from `Content.metadata` under `decision_factors`, `decision_confidence`, and `decision_reasons`.

## Evidence flow

Each factor creates one `Evidence` object. It contains its source, raw value, normalized value, weight, contribution, confidence, reason, and timestamp. Evidence is never discarded: every `Decision` contains the full evidence tuple and a matching `DecisionExplanation` tuple.

## Decision flow

The weighted score is compared with configurable create, review, and wait thresholds. The result becomes one of `CREATE`, `REVIEW`, `WAIT`, or `IGNORE`, with a deterministic summary and recommended action. `GET /decision/demo` exposes a placeholder example containing decision, evidence, and explanations.

## Configuration

`backend/app/core/decision_config.py` defines the v1 defaults. Environment variables use the `DECISION_` prefix, for example `DECISION_TREND_MOMENTUM_WEIGHT=0.30`. All weights must total `1.0`; thresholds are expressed on the `0–100` final-score scale.

## Future extension points

- Add repository-backed storage for decisions and evidence without changing the domain contracts.
- Add additional named factors by extending `DecisionConfig` and the engine factor map.
- Replace placeholder metadata producers with pipeline stages while preserving the same normalized inputs.
- Add audit and policy versions through the existing `Decision.version` field.
