# Training Notebooks

Use this directory for notebook-driven model development.

Start with:

- `01_xgboost_baseline.ipynb`

The notebook should be run from the `route_minds` Conda environment and should
import reusable helpers from `api/training/` instead of duplicating preprocessing
logic.

The current notebook flow is:

- inspect the raw simulation Parquet schema
- derive the canonical segment dataset
- run a stop-level smoke model for pipeline validation
- run the canonical segment travel-time model
- save model, metrics, schema, and config snapshot artifacts
