# RouteMinds

RouteMinds is a bus route rationalization system for Delhi transit. The repo
contains the ML training workflow, trained model artifacts, GTFS data inputs,
and the FastAPI backend for prediction, routing, and realtime enrichment.

## Project Overview

- Frontend lives in `apps/web` and shared UI components live in `packages/ui`.
- Backend APIs and services live under `api/app/`.
- Offline training code and notebooks live under `api/training/`.
- The current ML baseline uses XGBoost to predict segment travel time from a
  stop-event simulation dataset converted into segment-level examples.
- Model artifacts and evaluation metrics are written under `artifacts/`.

## Backend and ML Layout

```text
RouteMinds/
├── api/
│   ├── app/                  FastAPI app, inference, realtime, and routing services
│   ├── training/             Offline training code and notebook workflow
│   ├── tests/                Training pipeline tests
│   ├── TRAINING.md           Detailed training workflow notes
│   ├── environment.yml       Conda environment definition
│   └── requirements.txt      Python package list
├── data/
│   └── raw/
│       └── simulation/       Local simulation dataset placement
├── artifacts/
│   ├── models/               Saved trained pipelines and schemas
│   └── metrics/              Saved evaluation outputs and config snapshots
├── apps/
│   └── web/                  Frontend app
└── packages/
    └── ui/                   Shared frontend UI package
```

## Baseline Model

The current baseline is a two-part training workflow:

- `smoke`: a smaller stop-level run on `delay_minutes` to validate the pipeline
- `canonical`: the main segment-level XGBoost regressor on
  `actual_segment_minutes`

The canonical model is the important one for routing because graph edges need
segment travel cost, not cumulative stop delay.

High-level training flow:

1. Load the stop-event simulation Parquet dataset
2. Group by `trip_id` and derive segment rows from consecutive stops
3. Compute segment targets:
   - `scheduled_segment_minutes`
   - `actual_segment_minutes`
   - `segment_delay_minutes`
4. Derive temporal features from scheduled/query-time inputs, not realized GPS event time
5. Split train/validation/test by whole trips to reduce leakage
6. Fit an XGBoost regression pipeline
7. Save the trained model, schema, metrics, and config snapshot

## Training

Use only the Conda environment `route_minds`.

Notebook-first workflow:

```bash
cd api
conda run -n route_minds jupyter notebook
```

Open:

- `training/notebooks/01_xgboost_baseline.ipynb`

Run the notebook cells in order. The notebook bootstraps repo root into
`sys.path`, so `api.*` imports work even if Jupyter opens from the notebook
directory.

CLI workflow:

```bash
conda run -n route_minds python -m api.training.train_xgboost
```

The active training config is:

- `api/training/config/default_config.toml`

The detailed training notes are in:

- `api/TRAINING.md`

## Dataset and Artifacts

Current simulation source dataset:

- `data/raw/simulation/bus_delay_simulation.parquet`

Key outputs after training:

- `artifacts/models/xgboost_segment_travel_time_model.joblib`
- `artifacts/models/xgboost_segment_travel_time_schema.json`
- `artifacts/metrics/xgboost_segment_travel_time_metrics.json`
- `artifacts/metrics/xgboost_stop_delay_smoke_metrics.json`

## Backend Status

Current backend state:

- `api/app/main.py` wires the FastAPI app and routers
- `/api/v1/health` is available
- `/api/v1/predictions/segments` serves segment travel-time and delay predictions
- `/api/v1/routes/optimize` computes stop-to-stop paths using predicted segment costs
- `/api/v1/realtime/refresh` and `/api/v1/realtime/status` manage live GTFS-RT ingestion
- GTFS static graph construction, route optimization, and live enrichment are implemented
- Auth0 JWT verification protects route optimization and realtime operational endpoints

Run the backend from the repo root with:

```bash
conda run -n route_minds uvicorn api.app.main:app --reload
```

Prediction endpoint:

```text
POST /api/v1/predictions/segments
```

Required request fields per segment:

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

GTFS static files for backend graph construction live under:

- `data/raw/stops.txt`
- `data/raw/routes.txt`
- `data/raw/trips.txt`
- `data/raw/stop_times.txt`

Route optimization endpoint:

```text
POST /api/v1/routes/optimize
```

Required request fields:

- `origin_stop_id`
- `destination_stop_id`
- `query_timestamp_unix`

Realtime operational endpoints:

```text
POST /api/v1/realtime/refresh
GET /api/v1/realtime/status
```

Protected backend endpoints:

- `/api/v1/routes/optimize`
- `/api/v1/realtime/refresh`
- `/api/v1/realtime/status`

Auth0 backend settings:

- `AUTH0_ENABLED`
- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE`
- `AUTH0_ISSUER`
- `AUTH0_ALGORITHMS`
- `AUTH0_REALTIME_REQUIRED_PERMISSION`

Required real-time backend settings:

- `GTFS_RT_VEHICLE_POSITIONS_URL`
- `GTFS_RT_API_KEY`
- `GTFS_RT_AUTH_MODE`
- `GTFS_RT_API_KEY_QUERY_PARAM`
- `GTFS_RT_RESPONSE_FORMAT`
- `GTFS_RT_REFRESH_INTERVAL_SECONDS`
- `GTFS_RT_CACHE_MAX_AGE_SECONDS`
- `GTFS_RT_SNAPSHOT_PATH` (optional)

`GTFS_RT_REFRESH_INTERVAL_SECONDS` is used by the FastAPI background refresher to
periodically pull live vehicle positions when realtime is configured.
