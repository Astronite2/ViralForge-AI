# ViralForge AI Backend

ViralForge AI is a Content Intelligence Platform foundation designed for high-volume platform collection, event-driven processing, background work, and future AI-assisted analysis. This repository intentionally provides architecture only; it contains no product business logic, authentication implementation, or AI workflows.

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
