# Model Training

RouteMinds keeps offline training and online inference in the same repo, but with
separate responsibilities:

- `api/training/notebooks/` is the main place to run baseline experiments.
- `api/training/` contains reusable helpers that notebooks and scripts import.
- `api/app/` contains FastAPI and future inference-side services.
- `data/raw/simulation/` stores the local simulation source dataset.
- `artifacts/` stores trained models, metrics, schema metadata, and config snapshots.

## Dataset placement

The current simulation source dataset is:

`data/raw/simulation/bus_delay_simulation.parquet`

The training pipeline treats this file as a stop-event source table and derives the
canonical segment-level training frame from it.

If the path, format, or column names change, update:

- `api/training/config/default_config.toml`

## Training workflow

The canonical baseline is segment-level:

- source rows: stop events grouped by `trip_id`
- derived target: `actual_segment_minutes`
- secondary reporting target: `segment_delay_minutes`
- routing weight: predicted segment travel time

The notebook also includes a small stop-level smoke run using `delay_minutes` to
validate config and pipeline wiring, but that model is not the routing model.

## Train the baseline

Primary notebook workflow:

1. Launch Jupyter from `api/` in the `route_minds` environment:

   ```bash
   cd api
   conda run -n route_minds jupyter notebook
   ```

2. Open:

   - `training/notebooks/01_xgboost_baseline.ipynb`

Use the `route_minds` kernel inside Jupyter. Starting the notebook server from
`api/` is still preferred, but the notebook now bootstraps the `api/` root into
`sys.path`, so `training.*` imports also work when launched from
`api/training/notebooks/`.

Optional script entrypoint:

```bash
cd api
conda run -n route_minds python -m training.train_xgboost
```

With a custom config:

```bash
cd api
conda run -n route_minds python -m training.train_xgboost --config training/config/default_config.toml
```

## Outputs

Training writes:

- segment travel-time model to `artifacts/models/`
- canonical metrics to `artifacts/metrics/`
- stop-level smoke metrics to `artifacts/metrics/`
- feature schema to `artifacts/models/`
- resolved config snapshot to `artifacts/metrics/`

## Real-time follow-up

The real-time GTFS feed should not be trained directly from raw snapshot rows.
Instead:

- store raw API pulls separately
- enrich them with GTFS static context
- reconstruct stop/segment events
- emit the same segment feature contract used by the simulation baseline
