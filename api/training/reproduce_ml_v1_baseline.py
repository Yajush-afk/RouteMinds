from __future__ import annotations

import argparse
import json
import platform
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost

from api.app.services.prediction_service import _guard_prediction_minutes
from api.training.config import load_training_config, resolve_repo_path
from api.training.data import derive_segment_dataset, load_dataset, split_dataset
from api.training.evaluation_v2 import complete_evaluation
from api.training.features import build_training_frame

DEFAULT_OUTPUT_PATH = "artifacts/metrics/ml_v1_reproduction.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reproduce the runtime ML V1 baseline.")
    parser.add_argument("--output-path", default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def reproduce(output_path: str | Path = DEFAULT_OUTPUT_PATH) -> dict[str, object]:
    config = load_training_config("api/training/config/default_config.toml")
    raw = load_dataset(config)
    segments = derive_segment_dataset(raw, config)
    train, _, test = split_dataset(segments, config)
    features, _ = build_training_frame(
        test,
        config.segment_features,
        config.targets.canonical_target,
    )
    test_frame = test.loc[features.index].copy()

    model_path = resolve_repo_path(config.artifacts.model_path)
    captured_warnings: list[str] = []
    with warnings.catch_warnings(record=True) as warning_records:
        warnings.simplefilter("always")
        model = joblib.load(model_path)
        raw_predictions = model.predict(features)
        captured_warnings.extend(str(record.message) for record in warning_records)

    record_columns = (
        config.segment_features.categorical
        + [
            "stop_sequence",
            "normalized_stop_position",
            "distance_to_prev_stop_km",
            "segment_start_scheduled_unix",
            "scheduled_segment_minutes",
            "prev_segment_delay",
            "rolling_segment_delay_3",
        ]
    )
    records = test_frame[list(dict.fromkeys(record_columns))].to_dict("records")
    guarded_predictions = np.asarray(
        [
            _guard_prediction_minutes(
                prediction_minutes=float(prediction),
                record=record,
                model_supported=True,
            )
            for prediction, record in zip(raw_predictions, records, strict=True)
        ]
    )

    historical_means = (
        train.groupby(["route_id", "from_stop_id", "to_stop_id"], sort=False)[
            "actual_segment_minutes"
        ]
        .mean()
        .rename("historical_prediction")
    )
    historical = (
        test_frame.join(
            historical_means,
            on=["route_id", "from_stop_id", "to_stop_id"],
        )["historical_prediction"]
        .fillna(test_frame["scheduled_segment_minutes"])
        .to_numpy()
    )
    payload: dict[str, object] = {
        "status": "historical_v1_runtime_reproduction",
        "recorded_training_test_mae": 2.8918576075572284,
        "rows": len(test_frame),
        "target_quality": {
            "nonpositive_rows": int((test_frame["actual_segment_minutes"] <= 0).sum()),
            "nonpositive_fraction": float(
                (test_frame["actual_segment_minutes"] <= 0).mean()
            ),
        },
        "static_schedule": complete_evaluation(
            test_frame, test_frame["scheduled_segment_minutes"]
        ),
        "historical_average": complete_evaluation(test_frame, historical),
        "raw_ml_v1": complete_evaluation(test_frame, raw_predictions),
        "backend_guarded_ml_v1": complete_evaluation(test_frame, guarded_predictions),
        "artifact_load_warnings": captured_warnings,
        "runtime_versions": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "joblib": joblib.__version__,
        },
    }
    resolved_output = resolve_repo_path(str(output_path))
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    args = parse_args()
    result = reproduce(args.output_path)
    print(
        json.dumps(
            {
                "output_path": str(resolve_repo_path(args.output_path)),
                "recorded_training_test_mae": result["recorded_training_test_mae"],
                "raw_segment_mae": result["raw_ml_v1"]["segment"]["mae"],
                "guarded_segment_mae": result["backend_guarded_ml_v1"]["segment"]["mae"],
                "raw_trip_mae": result["raw_ml_v1"]["trip"]["mae"],
                "nonpositive_target_fraction": result["target_quality"][
                    "nonpositive_fraction"
                ],
                "artifact_load_warning_count": len(result["artifact_load_warnings"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
