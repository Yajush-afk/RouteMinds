# Model Training

## ML V2 status

ML V2 is the active retraining path. It keeps XGBoost, changes the target to
log slowdown, introduces leakage-safe categorical and historical features, and
produces native XGBoost P10/P50/P90 artifacts. LSTM and other neural networks are
not part of this cycle because reliable ordered realtime traces remain the data
bottleneck.

The backend activates V2 only when `MODEL_V2_MANIFEST_PATH` points to a valid
bundle. Missing, corrupt, incompatible, or invalid V2 predictions fall back to
the guarded legacy model and then to the static schedule.

### Reproduce ML V1

```bash
python -m api.training.reproduce_ml_v1_baseline
```

This writes `artifacts/metrics/ml_v1_reproduction.json` without replacing the
existing model.

### Generate and validate simulation data

```bash
python -m api.training.generate_segment_simulation_v2
python -m api.training.build_segment_dataset_v2 \
  --input-path data/processed/ml/simulation_v2_raw \
  --source simulation
```

The simulator uses seed 42, 28 service dates, cumulative monotonic timestamps,
and a two-million-segment cap. The builder writes rejection counts by quality
rule instead of silently discarding bad rows.

### Reconstruct realtime traces

```bash
python -m api.training.reconstruct_realtime_segments \
  --audit-path artifacts/metrics/realtime_trace_audit.json
python -m api.training.build_segment_dataset_v2 \
  --input-path data/processed/realtime/reconstructed_segments_v1 \
  --source realtime
```

The 200-trace audit must be manually labelled. Production promotion remains
blocked until the audit passes and there are at least 10,000 high-confidence
realtime segments across seven service dates.

Record the reviewed audit summary at
`artifacts/metrics/realtime_trace_audit_review_v2.json`:

```json
{
  "reviewed_trace_count": 200,
  "route_direction_accuracy": 0.92,
  "monotonic_progression_rate": 0.97
}
```

### Train ML V2

Use smoke mode first:

```bash
python -m api.training.train_xgboost_v2 --smoke --model-version smoke-v2
```

Then run the bounded CPU search and final candidates:

```bash
python -m api.training.train_xgboost_v2 --model-version YYYYMMDD-v2
```

Training uses at most 12 CPU threads, one model at a time, a one-million-row
tuning cap, and refuses to start with less than 10 GiB free. It materializes
versioned `float32` training, validation, and test feature Parquet under
`data/processed/ml/features_v2/` before fitting. The generated dataset is capped below the five-million-row threshold;
larger future datasets must first be materialized as numeric partitions and
trained with external-memory `QuantileDMatrix`.

To activate a promoted bundle:

```bash
export MODEL_V2_MANIFEST_PATH=artifacts/models/ml_v2/YYYYMMDD-v2/manifest.json
```

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
- feature time source: scheduled/query-time, not observed GPS event time
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
`api/` is still preferred, but the notebook now bootstraps the repo root into
`sys.path`, so `api.*` imports also work when launched from
`api/training/notebooks/`.

Optional script entrypoint:

```bash
conda run -n route_minds python -m api.training.train_xgboost
```

With a custom config:

```bash
conda run -n route_minds python -m api.training.train_xgboost --config api/training/config/default_config.toml
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
