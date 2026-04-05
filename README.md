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
- `/map`: map screen

The map experience currently focuses on:

- Delhi-area map interaction
- origin and destination placement
- place search
- reverse geocoding
- user location support

The frontend currently uses external map and geocoding services directly and does not yet call the RouteMinds backend APIs.

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
- `RouteOptimizationService`: scores route segments and computes best paths
- `RealtimeEnrichmentService`: fetches GTFS-RT vehicle positions and infers live segment delay context

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

## API Endpoints

The FastAPI app exposes the following routes under `/api/v1`:

- `GET /api/v1/auth/me`
- `GET /api/v1/health`
- `POST /api/v1/predictions/segments`
- `POST /api/v1/routes/optimize`
- `POST /api/v1/realtime/refresh`
- `GET /api/v1/realtime/status`

There is also a root route at `GET /` that returns app metadata and a docs pointer.

The backend also exposes unversioned aliases for the current API surface such as
`/auth/me`, `/health`, `/predictions/segments`, `/routes/optimize`, and `/realtime/*`.

### Authentication Contract

The current backend authentication contract is:

- authenticated: `GET /auth/me`, `GET /api/v1/auth/me`
- public: `GET /health`, `GET /api/v1/health`
- public: `POST /predictions/segments`, `POST /api/v1/predictions/segments`
- authenticated: `POST /routes/optimize`, `POST /api/v1/routes/optimize`
- authenticated plus `realtime:manage`: `GET /realtime/status`, `GET /api/v1/realtime/status`
- authenticated plus `realtime:manage`: `POST /realtime/refresh`, `POST /api/v1/realtime/refresh`

When `AUTH0_ENABLED=false`, backend auth dependencies are bypassed for local development.

`GET /auth/me` is the backend diagnostic endpoint for verifying that a caller is authenticated and inspecting the normalized claims, scopes, and permissions seen by the API.

The backend auth dependency layer is organized around:

- `require_auth` for bearer-token verification and normalized claims extraction
- `require_permissions(...)` for reusable permission-based authorization
- `require_realtime_access` as the realtime-specific permission guard built on top of `require_permissions(...)`

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

These folders are intended to hold generated and local data assets and are largely excluded from git.

## Local Development

### Prerequisites

- Bun `1.2.x`
- Node.js `>=20`
- Conda with an environment named `route_minds`

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
bun --cwd apps/web dev
```

Frontend build:

```bash
bun --cwd apps/web build
```

### Run the Backend

From the repository root:

```bash
conda run -n route_minds uvicorn api.app.main:app --reload
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

Auth0 settings include:

- `AUTH0_ENABLED`
- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE`
- `AUTH0_ISSUER`
- `AUTH0_ALGORITHMS`
- `AUTH0_REALTIME_REQUIRED_PERMISSION`

When `AUTH0_ENABLED=true`, the backend validates its Auth0 configuration at startup and fails early if:

- `AUTH0_DOMAIN` is missing
- `AUTH0_AUDIENCE` is missing
- `AUTH0_REALTIME_REQUIRED_PERMISSION` is missing
- `AUTH0_ISSUER` is not a valid `https://.../` tenant root
- `AUTH0_ISSUER` points to a different host than `AUTH0_DOMAIN`

`CORS_ALLOW_ORIGINS` must be a comma-separated list of bare origins such as
`http://localhost:5173,https://app.example.com`. Paths and query strings are rejected.

Recommended development values:

```env
AUTH0_ENABLED=true
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://routeminds-api
AUTH0_ISSUER=https://your-tenant.us.auth0.com/
AUTH0_ALGORITHMS=RS256
AUTH0_REALTIME_REQUIRED_PERMISSION=realtime:manage
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Recommended production values:

- set `AUTH0_ENABLED=true`
- use the production Auth0 tenant or custom domain consistently in both `AUTH0_DOMAIN` and `AUTH0_ISSUER`
- keep `AUTH0_ALGORITHMS=RS256` unless the tenant is explicitly configured otherwise
- set `CORS_ALLOW_ORIGINS` only to your deployed frontend origins
- do not leave localhost origins in production

If GTFS real-time settings are not configured, the real-time endpoints will not be operational.

## Testing

Backend tests live in `api/tests/` and currently cover:

- training pipeline behavior
- prediction API behavior
- GTFS graph construction
- route optimization API behavior
- real-time enrichment API behavior

## Implementation Notes

Some important realities about the current codebase:

- the backend is more mature than the frontend-backend integration
- route optimization is based on predicted segment travel time, not static shortest distance
- real-time support exists in the backend service layer, but depends on external GTFS-RT configuration and data availability
- there is no database or deployment stack in the repo yet, and Auth0-backed API authentication currently protects selected endpoints

## Near-Term Direction

The next practical milestone is connecting the frontend map workflow to the backend prediction and routing APIs so the product can demonstrate end-to-end dynamic route rationalization.
