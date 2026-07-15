# ViralForge AI

ViralForge helps creators decide what YouTube video to produce next by ranking
opportunities according to expected revenue potential, competition, longevity,
production effort and evidence confidence.

ViralForge Studio carries approved, source-grounded research into an Executive
Producer review that selects a defensible angle, production structure, evidence,
visual direction, and risks before script writing is unlocked.
The Script Writer then enforces duration-aware evidence sufficiency and produces
citation-mapped narration only when the approved evidence can support it.

[![CI](https://github.com/Astronite2/ViralForge-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Astronite2/ViralForge-AI/actions/workflows/ci.yml)

ViralForge AI combines its intelligence infrastructure with a working creator
production workspace. Projects progress through research and production-brief
approval while retaining evidence traceability and deterministic decisions.

Phase 5 adds the production Intelligence Dashboard in [`frontend/`](frontend/README.md). The read-only React application exposes the existing intelligence stack as a dark, responsive decision workspace without changing backend architecture or API contracts.

## Architecture

```text
HTTP API
   |
Services
   |
Repositories
   |
Domain objects
   |
PostgreSQL

Connectors / Agents / Workers are isolated integration boundaries.
```

Routes remain thin. They delegate orchestration to services, while repositories exclusively own persistence access. Domain objects are pure Python and never import SQLAlchemy.

An optional AI reasoning layer sits above the deterministic stack. It remains
disabled unless `AI_*` configuration is provided.

All connectors pass through the [Unified Signal Engine](docs/unified-signal-engine.md)
before knowledge ingestion and deterministic evaluation. Existing connector and
REST API contracts remain backward compatible.

Google Trends transport selection and degraded runtime behavior are documented in
the [Connector SDK guide](docs/connectors.md). The default pytrends provider is an
experimental fallback; no data is fabricated when it is unavailable.

Reddit Intelligence is disabled by default and uses Reddit's documented Data API
through OAuth only. See the [Reddit connector guide](docs/reddit-connector.md) for
configuration, supported post retrieval, and retention responsibilities.

## Folder structure

```text
backend/
  app/
    api/v1/          HTTP route layer
    core/            settings and cross-cutting configuration
    db/              SQLAlchemy engine and base
    models/          SQLAlchemy persistence models
    schemas/         Pydantic v2 API schemas
    repositories/    persistence boundaries
    services/        application-service boundaries
    domain/          pure business objects
    workers/         Celery application and task namespace
    connectors/      platform connector SDK
    agents/          future AI-agent namespaces
    dependencies/    FastAPI dependencies
    utils/           shared helpers
  tests/
alembic/              migration environment
```

## Prerequisites

- Python 3.13
- Node.js 22 and npm
- Docker and Docker Compose
- PostgreSQL and Redis when running services outside Docker

## Docker startup

```bash
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`.
API docs are available at `http://localhost:8000/docs`.
Flower is exposed at `http://localhost:5555`.
Readiness is available at `GET /ready`.
Liveness is available at `GET /health`.
The reasoning APIs are available under `/api/v1/reasoning/*` when enabled.

## Intelligence Dashboard

With the API running, start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The development server proxies REST requests to `http://localhost:8000`; set `VITE_API_URL` for a different API origin. See the [frontend README](frontend/README.md) for architecture and verification commands.

## Alembic migrations

Use the configured environment after setting `DATABASE_URL`:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

To create a new migration:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Alembic loads all SQLAlchemy model metadata from `backend.app.models`.

## Running tests

```bash
python -m pip install -e ".[dev]"
ruff check backend alembic
black --check backend alembic
pytest
```

## Continuous integration

GitHub Actions runs the repository quality gate for every pull request and for pushes to `main` and `feature/**` branches. Superseded runs on the same branch or pull request are cancelled automatically.

The required jobs are:

| Job | Checks |
| --- | --- |
| Backend quality | Ruff, Black, the complete Pytest suite, and an Alembic upgrade/downgrade/re-upgrade lifecycle on a disposable database |
| PostgreSQL integration | PostgreSQL 16 and Redis service health, Alembic upgrade to head, content insert/update persistence, `/health`, and `/ready` |
| Frontend quality | `npm ci`, Oxlint, Vitest, strict TypeScript compilation, and the Vite production build |
| Repository hygiene | Tracked `.env` files, generated caches, required migrations and lockfile, and common committed-secret signatures |
| Docker validation | Compose configuration validation and the production API image build |
| Quality gate | Requires every preceding job to complete successfully |

CI uses only disposable local credentials. AI reasoning and YouTube access are disabled, and no live provider keys are required.

Run the equivalent quality checks locally from the repository root:

```bash
python3 -m pytest -q
python3 -m ruff check backend alembic scripts
python3 -m black --check backend alembic scripts
python3 scripts/check_repository_hygiene.py

cd frontend
npm ci
npm run lint
npm run test
npm run build
cd ..

docker compose config --quiet
docker build .
```

The frontend build runs `tsc -b` before Vite, so a successful build includes the strict TypeScript check.

### Troubleshooting CI

- Backend failures: reproduce with Python 3.13 and install `.[dev]`; keep `AI_REASONING_ENABLED=false` when testing the disabled-provider behavior.
- PostgreSQL failures: inspect the service health output first, then verify `DATABASE_URL` targets a disposable PostgreSQL 16 database and run `python3 -m alembic upgrade head`.
- Frontend failures: use Node.js 22 and `npm ci`; do not replace the committed lockfile with an install from a different dependency tree.
- Docker failures: run `docker compose config` before rebuilding to separate configuration errors from image-build errors.
- Hygiene failures report only the filename and signature category. Remove the credential from Git history and rotate it; never print or recommit the value.

## Running the demo flow

```bash
make demo-intelligence-flow
```

The demo runs a fixture-backed signal through normalization, event emission,
decision evaluation, persistence, and read-back verification using the
configured application database. For isolated local testing:

```bash
python -m backend.scripts.demo_intelligence_flow --database-mode isolated
```

## Readiness and observability

- `GET /ready` checks PostgreSQL and Redis.
- `GET /health` preserves the existing liveness check.
- Worker logs and beat logs are visible in the Docker Compose output.
- Flower is available at `http://localhost:5555`.

## Development workflow

1. Create a migration whenever persistence models change.
2. Keep API routes limited to transport concerns and dependency wiring.
3. Put use-case orchestration in services, persistence in repositories, and infrastructure-independent concepts in domain objects.
4. Add platform integrations through `BaseConnector`; background entry points belong in `workers/tasks.py`.
5. Run format, lint, and tests before opening a pull request. GitHub Actions repeats these checks and builds the Docker image.

## Evidence recovery

When the Script Writer finds insufficient evidence, ViralForge can run a focused, versioned research expansion. Expanded research invalidates stale Production Brief and Script approvals; each downstream artifact records its upstream versions. Thresholds remain unchanged and failed expansion preserves the prior approved dossier. See [Research expansion](docs/research-expansion.md).
