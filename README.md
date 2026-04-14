# RouteMinds

RouteMinds is a Delhi transit intelligence project focused on route rationalization, delay prediction, and route selection using machine learning, GTFS data, and real-time operational context.

## Problem Statement

This project is built around the following problem statement:

> "Dynamic route rationalization model based on machine learning/AI would be required based on real-time traffic and road parameters."

RouteMinds approaches this by combining:

- offline ML training for segment travel-time prediction
- GTFS-based transit graph construction
- route optimization using predicted segment costs
- real-time vehicle-position enrichment to inject live delay context into routing decisions

## Current State

The repository currently contains three main parts:

1. `apps/web`: a React frontend with a landing page and an interactive Delhi-focused map experience
2. `packages/ui`: a shared UI package used by the frontend
3. `api`: a FastAPI backend plus the offline ML training pipeline

What is working today:

- frontend landing page and map interface
- place search and reverse geocoding through OpenStreetMap Nominatim
- MapLibre-based map rendering using OpenFreeMap styles
- FastAPI health, segment prediction, route optimization, and real-time endpoints
- XGBoost-based segment travel-time model training
- GTFS static graph construction from stops, trips, routes, and stop times
- Dijkstra-based route optimization over predicted segment travel times
- GTFS-RT vehicle-position ingestion with live segment delay enrichment support
- live corridor instability, bunching, and headway irregularity proxies from GTFS-RT
- wait-aware and reliability-aware route scoring with ETA ranges
- generalized route cost scoring with transfer, uncertainty, reliability, and detour penalties
- route explanations, congestion-proxy outputs, and service-quality indicators in route responses
- backend test coverage for training, prediction, routing, GTFS graph logic, and real-time enrichment

What is not complete yet:

- the frontend is not yet wired to the backend routing and prediction APIs
- deployment and CI/CD configuration are not present in the repository
- the project currently uses local files for GTFS data, datasets, and model artifacts rather than a database-backed platform

## Repository Layout

```text
RouteMinds/
├── apps/
│   └── web/                  React + Vite frontend
├── packages/
│   └── ui/                   Shared UI system and styles
├── api/
│   ├── app/                  FastAPI app, schemas, services, ML inference helpers
│   ├── training/             Offline model training code and notebooks
│   ├── tests/                Backend and training tests
│   ├── TRAINING.md           Training workflow notes
│   ├── environment.yml       Conda environment definition
│   └── requirements.txt      Python dependencies
├── data/
│   └── raw/                  Local GTFS and simulation data
├── artifacts/
│   ├── models/               Saved trained models and schema metadata
│   └── metrics/              Evaluation outputs and config snapshots
├── package.json              Bun workspace root
└── turbo.json                Turborepo task configuration
```

## Architecture

### Frontend

The frontend is built with:

- React 19
- TypeScript
- Vite
- React Router
- MapLibre GL and `react-map-gl`
- Tailwind CSS v4
- shared shadcn-style UI components from `packages/ui`

Current routes:

- `/`: landing page
- `/auth`: Supabase sign-in page with Google OAuth and one-time codes
- `/map`: protected map screen

The map experience currently focuses on:

- Delhi-area map interaction
- origin and destination placement
- place search
- reverse geocoding
- user location support

The frontend keeps the current main map implementation as the source of truth for map UX. `/map` is login-gated through Supabase, while `/` and `/auth` remain public.

Frontend auth settings include:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY`

Authenticated frontend API calls forward the active Supabase bearer token to the backend.

### Backend

The backend is built with:

- FastAPI
- Pydantic
- Pandas
- scikit-learn
- XGBoost
- HTTPX

The backend service layer currently includes:

- `PredictionService`: loads the trained model and predicts segment travel times
- `GTFSGraphService`: builds a directed transit graph from GTFS static files
- `RouteOptimizationService`: scores route segments and computes best paths using generalized route cost
- `RealtimeEnrichmentService`: fetches GTFS-RT vehicle positions and infers live delay, slowdown, bunching, and service-quality context

### Machine Learning

The current baseline model predicts segment-level travel time, which is the quantity needed for routing.

High-level training flow:

1. Load the stop-event simulation dataset
2. Group rows by `trip_id`
3. Convert consecutive stop events into segment-level records
4. Build temporal and route features
5. Split by trip to reduce leakage
6. Train an XGBoost regressor
7. Save model artifacts, schema metadata, metrics, and config snapshot

This model is used by the backend to estimate segment travel cost during route optimization.

Current prototype routing layers on top of the model now also expose:

- segment uncertainty and route reliability scores
- ETA ranges instead of a single point estimate only
- slowdown-based congestion proxies instead of unsupported direct traffic density claims
- transfer fragility and missed-transfer risk signals
- service-quality and corridor-instability indicators derived from GTFS-RT

## API Endpoints

The FastAPI app exposes the following routes under `/api/v1`:

- `GET /api/v1/auth/me`
- `GET /api/v1/health`
- `POST /api/v1/predictions/segments`
- `GET /api/v1/stops/nearby`
- `POST /api/v1/routes/optimize`
- `POST /api/v1/realtime/refresh`
- `GET /api/v1/realtime/status`

There is also a root route at `GET /` that returns app metadata and a docs pointer.

The backend also exposes unversioned aliases for the current API surface such as
`/auth/me`, `/health`, `/stops/nearby`, `/predictions/segments`, `/routes/optimize`, and `/realtime/*`.

### Authentication Contract

The current backend authentication contract is:

- authenticated: `GET /auth/me`, `GET /api/v1/auth/me`
- public: `GET /health`, `GET /api/v1/health`
- public: `POST /predictions/segments`, `POST /api/v1/predictions/segments`
- authenticated: `GET /stops/nearby`, `GET /api/v1/stops/nearby`
- authenticated: `POST /routes/optimize`, `POST /api/v1/routes/optimize`
- authenticated plus `realtime:manage`: `GET /realtime/status`, `GET /api/v1/realtime/status`
- authenticated plus `realtime:manage`: `POST /realtime/refresh`, `POST /api/v1/realtime/refresh`

When `SUPABASE_AUTH_ENABLED=false`, backend auth dependencies are bypassed for local development.

`GET /auth/me` is the backend diagnostic endpoint for verifying that a caller is authenticated and inspecting the normalized claims and permissions seen by the API.

Authenticated API routes require a real Supabase user session token, not just any signed JWT. The backend expects at least:

- a non-empty `sub`
- `role=authenticated`
- a non-empty `session_id`
- `is_anonymous=false` when the claim is present

Realtime authorization reads permissions primarily from `app_metadata.permissions` in the Supabase access token. Legacy root-level `permissions` and `scope` claims are still accepted for compatibility.

The backend auth dependency layer is organized around:

- `require_auth` for bearer-token verification and normalized claims extraction
- `require_permissions(...)` for reusable permission-based authorization
- `require_realtime_access` as the realtime-specific permission guard built on top of `require_permissions(...)`

Auth failures are logged with safe metadata only. The backend records the request path, auth event type, subject when available, and missing permissions when relevant. Raw bearer tokens are never logged.

### Prediction Request Shape

The segment prediction endpoint expects segment records containing:

- `route_id`
- `from_stop_id`
- `to_stop_id`
- `stop_sequence`
- `normalized_stop_position`
- `distance_to_prev_stop_km`
- `segment_start_scheduled_unix`
- `scheduled_segment_minutes`
- `prev_segment_delay`
- `rolling_segment_delay_3`

### Route Optimization Request Shape

The route optimization endpoint expects:

- `origin_stop_id`
- `destination_stop_id`
- `query_timestamp_unix`

### Route Optimization Response Highlights

The route optimization response now exposes prototype-ready explanation and risk fields,
including:

- total predicted ETA
- ETA lower and upper range
- route reliability score
- generalized route cost and cost breakdown
- total wait and in-vehicle time
- congestion proxy ratio and slowdown percentage
- transfer count, fragile transfer count, and transfer fragility score
- segment-level transfer, reliability, and penalty details
- human-readable route selection reasons

## Data and Artifacts

The project currently relies on local files rather than a database.

Important inputs:

- simulation dataset: `data/raw/simulation/bus_delay_simulation.parquet`
- GTFS static files:
  - `data/raw/stops.txt`
  - `data/raw/routes.txt`
  - `data/raw/trips.txt`
  - `data/raw/stop_times.txt`

Important outputs:

- trained model in `artifacts/models/`
- feature schema in `artifacts/models/`
- metrics and config snapshots in `artifacts/metrics/`
- realtime canonicalization and hybrid reconstruction reports in `artifacts/metrics/`

These folders are intended to hold generated and local data assets and are largely excluded from git.

## Local Development

### Prerequisites

- Bun `1.2.x`
- Node.js `>=20`
- Conda with an environment named `route_minds`

### One-Time Setup

From the repository root:

```bash
bun install
conda env create -f environment.yml
```

If the Conda env already exists and you want to sync it with the repo definition:

```bash
conda env update -n route_minds -f environment.yml --prune
```

### Workspace Commands

From the repository root:

```bash
bun dev
bun build
bun lint
bun typecheck
```

These commands use Turborepo for workspace task orchestration.

### Run the Frontend

From the repository root:

```bash
bun run web:dev
```

The frontend dev server URL is printed by Vite in the terminal.

Frontend build:

```bash
bun --cwd apps/web build
```

### Run the Backend

From the repository root:

```bash
bun run api:start
```

Useful backend lifecycle commands from the repository root:

```bash
bun run api:status
bun run api:stop
bun run api:restart
```

By default the backend runs on `127.0.0.1:8000`. To use another port:

```bash
BACKEND_PORT=8001 bun run api:start
```

To run frontend and backend together, use two terminals:

```bash
# terminal 1
bun run web:dev

# terminal 2
bun run api:start
```

Swagger UI will be available at:

```text
http://127.0.0.1:8000/docs
```

### Train the Model

Notebook workflow:

```bash
conda run -n route_minds jupyter notebook
```

Open:

- `api/training/notebooks/01_xgboost_baseline.ipynb`

CLI workflow:

```bash
conda run -n route_minds python -m api.training.train_xgboost
```

Detailed notes are available in `api/TRAINING.md`.

## Backend Configuration

The backend reads configuration from environment variables and `.env`.

Core backend settings include:

- `MODEL_PATH`
- `SCHEMA_PATH`
- `GTFS_STATIC_DIR`
- `GTFS_RT_VEHICLE_POSITIONS_URL`
- `GTFS_RT_API_KEY`
- `GTFS_RT_AUTH_MODE`
- `GTFS_RT_API_KEY_QUERY_PARAM`
- `GTFS_RT_RESPONSE_FORMAT`
- `GTFS_RT_REFRESH_INTERVAL_SECONDS`
- `GTFS_RT_CACHE_MAX_AGE_SECONDS`
- `GTFS_RT_SNAPSHOT_PATH`

Supabase auth settings include:

- `SUPABASE_AUTH_ENABLED`
- `SUPABASE_URL`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWT_AUDIENCE`
- `SUPABASE_JWT_ALGORITHMS`
- `SUPABASE_REALTIME_REQUIRED_PERMISSION`

When `SUPABASE_AUTH_ENABLED=true`, the backend validates its Supabase JWT configuration at startup and fails early if:

- `SUPABASE_URL` is missing
- `SUPABASE_JWT_AUDIENCE` is missing
- `SUPABASE_REALTIME_REQUIRED_PERMISSION` is missing
- `SUPABASE_JWT_ISSUER` is not a valid `https://.../auth/v1` issuer URL
- `SUPABASE_JWT_ISSUER` points to a different host than `SUPABASE_URL`
- `SUPABASE_JWT_ALGORITHMS` includes unsupported shared-secret algorithms such as `HS256`

`CORS_ALLOW_ORIGINS` must be a comma-separated list of bare origins such as
`http://localhost:5173,https://app.example.com`. Paths and query strings are rejected.

Recommended development values:

```env
SUPABASE_AUTH_ENABLED=true
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_JWT_ISSUER=https://your-project-ref.supabase.co/auth/v1
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ALGORITHMS=RS256
SUPABASE_REALTIME_REQUIRED_PERMISSION=realtime:manage
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Recommended production values:

- set `SUPABASE_AUTH_ENABLED=true`
- use the production Supabase project origin consistently in both `SUPABASE_URL` and `SUPABASE_JWT_ISSUER`
- keep `SUPABASE_JWT_ALGORITHMS=RS256` unless the project is explicitly configured otherwise
- set `CORS_ALLOW_ORIGINS` only to your deployed frontend origins
- do not leave localhost origins in production

If GTFS real-time settings are not configured, the real-time endpoints will not be operational.

## Testing

Backend tests live in `api/tests/` and currently cover:

- training pipeline behavior
- prediction API behavior
- GTFS graph construction
- stops API behavior
- route optimization API behavior
- real-time enrichment API behavior
- Supabase auth configuration validation
- auth dependency behavior, including malformed bearer headers, invalid audience, invalid issuer, expired tokens, and permission failures

API-focused test commands:

```bash
conda run -n route_minds python -m unittest api.tests.test_config
conda run -n route_minds python -m unittest api.tests.test_auth_api
conda run -n route_minds python -m unittest api.tests.test_stops_api
conda run -n route_minds python -m unittest api.tests.test_route_optimization_api
conda run -n route_minds python -m unittest api.tests.test_realtime_enrichment_api
bun --cwd apps/web typecheck
```

Optional live Supabase verification is available through an environment-gated integration test:

```bash
export ROUTEMINDS_SUPABASE_TEST_BASE_URL=http://127.0.0.1:8000
export ROUTEMINDS_SUPABASE_TEST_ACCESS_TOKEN=<valid access token>
export ROUTEMINDS_SUPABASE_TEST_REALTIME_TOKEN=<token with realtime:manage>
export ROUTEMINDS_SUPABASE_TEST_INVALID_TOKEN=<known invalid token>
conda run -n route_minds python -m unittest api.tests.test_supabase_live_integration
```

Only `ROUTEMINDS_SUPABASE_TEST_BASE_URL` and `ROUTEMINDS_SUPABASE_TEST_ACCESS_TOKEN` are required to enable the live suite. The realtime and invalid-token checks are skipped unless those extra variables are set.

## Auth Rollout

Recommended rollout sequence for backend Supabase JWT enforcement:

1. Set and validate all Supabase auth env vars in a development environment.
2. Start the backend and confirm `/health` stays public.
3. Verify `/auth/me` returns `401` without a token and `200` with a valid token.
4. Verify `/routes/optimize` returns `401` without a token and succeeds with a valid authenticated token.
5. Verify `/realtime/status` and `/realtime/refresh` return `403` for tokens missing `realtime:manage` and `200` for tokens that include it.
6. Run the local auth-focused unit suites and, when project credentials are available, the live Supabase integration suite.
7. Promote the same environment contract to your shared or production environment, limiting `CORS_ALLOW_ORIGINS` to deployed frontend origins only.

## Implementation Notes

Some important realities about the current codebase:

- the backend is more mature than the frontend-backend integration
- route optimization is based on predicted segment travel time, not static shortest distance
- real-time support exists in the backend service layer, but depends on external GTFS-RT configuration and data availability
- there is no database or deployment stack in the repo yet, and Supabase-backed API authentication currently protects selected endpoints

## Near-Term Direction

The next practical milestone is connecting the frontend map workflow to the backend prediction and routing APIs so the product can demonstrate end-to-end dynamic route rationalization.
