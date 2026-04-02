# RouteMinds

RouteMinds is a bus route rationalization system for Delhi transit. The current
repo focus is backend and ML infrastructure: offline training, model artifacts,
and the FastAPI backend that will later orchestrate prediction and routing.

## Current Status

- Frontend exists in `apps/web` and shared UI exists in `packages/ui`, but they
  are out of scope for the current backend/ML work.
- The backend FastAPI skeleton exists under `api/app/`.
- The first ML baseline is implemented and trained under `api/training/`.
- The current baseline uses XGBoost to predict segment travel time from a
  stop-event simulation dataset converted into segment-level examples.
- Model artifacts and evaluation metrics are written under `artifacts/`.

## Backend and ML Layout

```text
RouteMinds/
├── api/
│   ├── app/                  FastAPI app, future inference and routing services
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
│   └── web/                  Frontend app (not modified in current ML/backend work)
└── packages/
    └── ui/                   Shared frontend UI package (not modified)
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
- route optimization and prediction endpoints are still placeholders
- inference-side model loading utilities exist, but end-to-end API integration
  is not complete yet

Run the backend from the repo root with:

```bash
conda run -n route_minds uvicorn api.app.main:app --reload
```

Phase 1 prediction endpoint:

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

Phase 3 route optimization endpoint:

```text
POST /api/v1/routes/optimize
```

Required request fields:

- `origin_stop_id`
- `destination_stop_id`
- `query_timestamp_unix`

## Next Recommended Step

The next backend milestone is real-time enrichment and inference integration:

1. ingest raw GTFS-RT vehicle snapshots
2. join them with GTFS static trip/stop-time context
3. reconstruct the same segment feature contract used in training
4. call the trained model for segment travel-time prediction
5. feed predicted segment costs into the future routing engine
