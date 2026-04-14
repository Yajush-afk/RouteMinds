from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from api.training.config import load_training_config, resolve_repo_path
from api.training.data import derive_segment_dataset, load_dataset, split_dataset
from api.training.features import build_training_frame

DEFAULT_CONFIG_PATH = "api/training/config/default_config.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate RouteMinds segment/trip ETA baselines against the current ML model."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--output-path",
        default="artifacts/metrics/routing_baseline_evaluation.json",
    )
    return parser.parse_args()


def _regression_metrics(actual: pd.Series, predicted: pd.Series) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(root_mean_squared_error(actual, predicted)),
        "r2": float(r2_score(actual, predicted)),
    }


def _historical_average_predictions(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
) -> pd.Series:
    grouped_means = (
        train_frame.groupby(["route_id", "from_stop_id", "to_stop_id"], sort=False)[
            "actual_segment_minutes"
        ]
        .mean()
        .rename("historical_average_segment_minutes")
    )
    lookup_frame = test_frame.join(
        grouped_means,
        on=["route_id", "from_stop_id", "to_stop_id"],
    )
    return lookup_frame["historical_average_segment_minutes"].fillna(
        lookup_frame["scheduled_segment_minutes"]
    )


def _trip_level_metrics(
    frame: pd.DataFrame,
    *,
    actual_column: str,
    prediction_columns: dict[str, str],
) -> dict[str, dict[str, float]]:
    trip_frame = (
        frame.groupby("trip_id", sort=False)
        .agg({actual_column: "sum", **{column: "sum" for column in prediction_columns.values()}})
        .reset_index(drop=True)
    )
    metrics: dict[str, dict[str, float]] = {}
    actual = trip_frame[actual_column]
    for name, column in prediction_columns.items():
        metrics[name] = _regression_metrics(actual, trip_frame[column])
    return metrics


def evaluate_baselines(config_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    config = load_training_config(config_path)
    raw_frame = load_dataset(config)
    segment_frame = derive_segment_dataset(raw_frame, config)
    train_frame, _, test_frame = split_dataset(segment_frame, config)

    schema_path = resolve_repo_path(config.artifacts.schema_path)
    model_path = resolve_repo_path(config.artifacts.model_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    model = joblib.load(model_path)

    feature_frame, target = build_training_frame(
        test_frame,
        feature_config=type(
            "FeatureConfigShim",
            (),
            {
                "categorical": schema["categorical_features"],
                "numeric": schema["numeric_features"],
                "drop": schema.get("drop_columns", []),
                "feature_time_column": schema.get("feature_time_column", "segment_start_scheduled_unix"),
            },
        )(),
        target_column="actual_segment_minutes",
    )

    schedule_predictions = test_frame.loc[feature_frame.index, "scheduled_segment_minutes"].reset_index(drop=True)
    historical_predictions = _historical_average_predictions(
        train_frame,
        test_frame.loc[feature_frame.index].copy(),
    ).reset_index(drop=True)
    ml_predictions = pd.Series(model.predict(feature_frame), index=feature_frame.index, name="ml_predictions")

    evaluation_frame = test_frame.loc[feature_frame.index].copy().reset_index(drop=True)
    evaluation_frame["scheduled_prediction_minutes"] = schedule_predictions.values
    evaluation_frame["historical_prediction_minutes"] = historical_predictions.values
    evaluation_frame["ml_prediction_minutes"] = ml_predictions.reset_index(drop=True).values
    evaluation_frame["ml_uncertainty_proxy_minutes"] = (
        (evaluation_frame["ml_prediction_minutes"] - evaluation_frame["scheduled_segment_minutes"]).abs() * 0.18
        + 0.6
    )
    evaluation_frame["risk_adjusted_prediction_minutes"] = (
        evaluation_frame["ml_prediction_minutes"]
        + evaluation_frame["ml_uncertainty_proxy_minutes"] * 0.15
    )

    segment_metrics = {
        "static_schedule": _regression_metrics(
            evaluation_frame["actual_segment_minutes"],
            evaluation_frame["scheduled_prediction_minutes"],
        ),
        "historical_average": _regression_metrics(
            evaluation_frame["actual_segment_minutes"],
            evaluation_frame["historical_prediction_minutes"],
        ),
        "current_mean_eta_ml": _regression_metrics(
            evaluation_frame["actual_segment_minutes"],
            evaluation_frame["ml_prediction_minutes"],
        ),
        "reliability_adjusted_ml": _regression_metrics(
            evaluation_frame["actual_segment_minutes"],
            evaluation_frame["risk_adjusted_prediction_minutes"],
        ),
    }

    trip_metrics = _trip_level_metrics(
        evaluation_frame,
        actual_column="actual_segment_minutes",
        prediction_columns={
            "static_schedule": "scheduled_prediction_minutes",
            "historical_average": "historical_prediction_minutes",
            "current_mean_eta_ml": "ml_prediction_minutes",
            "reliability_adjusted_ml": "risk_adjusted_prediction_minutes",
        },
    )

    interval_lower = evaluation_frame["ml_prediction_minutes"] - evaluation_frame["ml_uncertainty_proxy_minutes"]
    interval_upper = evaluation_frame["ml_prediction_minutes"] + evaluation_frame["ml_uncertainty_proxy_minutes"]
    reliability_metrics = {
        "segment_interval_coverage": float(
            ((evaluation_frame["actual_segment_minutes"] >= interval_lower)
             & (evaluation_frame["actual_segment_minutes"] <= interval_upper)).mean()
        ),
        "mean_uncertainty_proxy_minutes": float(evaluation_frame["ml_uncertainty_proxy_minutes"].mean()),
    }

    payload: dict[str, Any] = {
        "dataset_path": str(resolve_repo_path(config.data.dataset_path)),
        "model_path": str(model_path),
        "schema_path": str(schema_path),
        "segment_row_count": int(len(segment_frame)),
        "test_row_count": int(len(evaluation_frame)),
        "segment_metrics": segment_metrics,
        "trip_metrics": trip_metrics,
        "reliability_metrics": reliability_metrics,
        "notes": {
            "weather_evaluation": "Deferred until a stable weather-joined dataset is available.",
            "road_context_evaluation": "Deferred until explicit road-context features are added to model training.",
            "congestion_proxy_evaluation": "Current prototype uses slowdown-based live congestion proxies in routing/explanations rather than retrained model features.",
        },
    }

    resolved_output_path = resolve_repo_path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    args = parse_args()
    payload = evaluate_baselines(args.config, args.output_path)
    print("Baseline evaluation finished.")
    print(f"Dataset: {payload['dataset_path']}")
    print(f"Output: {resolve_repo_path(args.output_path)}")
    print(f"Segment baselines: {', '.join(payload['segment_metrics'].keys())}")


if __name__ == "__main__":
    main()
