# ViralForge Intelligence Dashboard

Production React client for ViralForge AI's decision-intelligence APIs. It is a read-only, desktop-first interface for topics, connector signals, opportunities, deterministic decisions, evidence, historical analytics, AI reasoning, and knowledge relationships.

## Stack

- React 19, strict TypeScript, and Vite
- Tailwind CSS
- TanStack Query for cache, retries, cancellation, and request state
- Recharts for intelligence charts
- React Flow for the interactive knowledge graph
- React Router with lazy-loaded route bundles
- Vitest and Testing Library

## Run locally

Start the API at `http://localhost:8000`, then:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the dashboard at `http://localhost:5173` and proxies API traffic to port 8000. To use another API host, create `frontend/.env.local`:

```bash
VITE_API_URL=http://localhost:8000
```

## Verification

```bash
npm run lint
npm run test
npm run build
```

The production output is written to `frontend/dist`.

## Structure

```text
src/
  api/           typed REST client, API types, query keys and hooks
  components/    reusable cards, badges, states, evidence and metrics
  features/      route-level feature modules
  layout/        responsive application shell and global navigation
  lib/           data-formatting utilities
  test/          shared test setup
```

## API behavior

The dashboard uses existing REST routes only. It does not create mock records when APIs return empty. Empty data, offline connectors, unavailable backends, disabled/no-output AI, and request timeouts each render an explicit non-crashing state. Global AI reasoning history is assembled from the existing per-topic reasoning route because the backend intentionally has no global reasoning-list endpoint.
