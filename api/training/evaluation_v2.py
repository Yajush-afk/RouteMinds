from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error


def regression_metrics(actual, predicted) -> dict[str, float]:
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    absolute_errors = np.abs(actual_values - predicted_values)
    return {
        "mae": float(mean_absolute_error(actual_values, predicted_values)),
        "rmse": float(root_mean_squared_error(actual_values, predicted_values)),
        "r2": float(r2_score(actual_values, predicted_values)),
        "p90_absolute_error": float(np.quantile(absolute_errors, 0.9)),
    }


def trip_metrics(
    frame: pd.DataFrame,
    predictions,
    *,
    actual_column: str = "actual_segment_minutes",
) -> dict[str, float]:
    group_columns = [
        column for column in ("source", "service_date", "trip_id") if column in frame
    ]
    if "trip_id" not in group_columns:
        raise ValueError("Complete-trip evaluation requires trip_id.")
    evaluation = frame[group_columns + [actual_column]].copy()
    evaluation["prediction"] = np.asarray(predictions, dtype=float)
    trips = evaluation.groupby(group_columns, sort=False, dropna=False)[
        [actual_column, "prediction"]
    ].sum()
    metrics = regression_metrics(trips[actual_column], trips["prediction"])
    metrics["trip_count"] = int(len(trips))
    return metrics


def trip_length_error_report(
    frame: pd.DataFrame,
    predictions,
) -> list[dict[str, Any]]:
    group_columns = [
        column for column in ("source", "service_date", "trip_id") if column in frame
    ]
    evaluation = frame[group_columns + ["actual_segment_minutes"]].copy()
    evaluation["prediction"] = np.asarray(predictions, dtype=float)
    trips = evaluation.groupby(group_columns, sort=False, dropna=False).agg(
        actual=("actual_segment_minutes", "sum"),
        prediction=("prediction", "sum"),
        segment_count=("prediction", "size"),
    )
    trips["absolute_error"] = (trips["actual"] - trips["prediction"]).abs()
    trips["trip_length_bucket"] = pd.cut(
        trips["segment_count"],
        bins=[0, 5, 10, 20, 40, np.inf],
        labels=["1-5", "6-10", "11-20", "21-40", "41+"],
    )
    grouped = trips.groupby("trip_length_bucket", observed=True)["absolute_error"].agg(
        ["mean", "count"]
    )
    return [
        {
            "trip_length_bucket": str(index),
            "mae": float(row["mean"]),
            "trips": int(row["count"]),
        }
        for index, row in grouped.iterrows()
    ]


def interval_coverage(actual, lower, upper) -> float:
    actual_values = np.asarray(actual, dtype=float)
    lower_values = np.asarray(lower, dtype=float)
    upper_values = np.asarray(upper, dtype=float)
    return float(((actual_values >= lower_values) & (actual_values <= upper_values)).mean())


def grouped_error_report(
    frame: pd.DataFrame,
    predictions,
    *,
    group_column: str,
    max_groups: int = 50,
) -> list[dict[str, Any]]:
    evaluation = frame[[group_column, "actual_segment_minutes"]].copy()
    evaluation["prediction"] = np.asarray(predictions, dtype=float)
    evaluation["absolute_error"] = (
        evaluation["actual_segment_minutes"] - evaluation["prediction"]
    ).abs()
    grouped = (
        evaluation.groupby(group_column, dropna=False, sort=False)["absolute_error"]
        .agg(["mean", "count"])
        .sort_values(["count", "mean"], ascending=[False, False])
        .head(max_groups)
    )
    return [
        {
            group_column: str(index),
            "mae": float(row["mean"]),
            "rows": int(row["count"]),
        }
        for index, row in grouped.iterrows()
    ]


def complete_evaluation(
    frame: pd.DataFrame,
    predictions,
    *,
    lower=None,
    upper=None,
) -> dict[str, Any]:
    predicted_values = np.asarray(predictions, dtype=float)
    payload: dict[str, Any] = {
        "rows": int(len(frame)),
        "segment": regression_metrics(frame["actual_segment_minutes"], predicted_values),
        "trip": trip_metrics(frame, predicted_values),
        "nonpositive_prediction_count": int((predicted_values <= 0.0).sum()),
        "error_by_route": grouped_error_report(
            frame, predicted_values, group_column="route_id"
        ),
        "error_by_trip_length": trip_length_error_report(frame, predicted_values),
        "fallback_rate": 0.0,
    }
    timestamps = pd.to_datetime(
        frame["segment_start_scheduled_unix"], unit="s", utc=True
    ).dt.tz_convert("Asia/Kolkata")
    time_frame = frame.assign(time_bucket=(timestamps.dt.hour // 3).astype(str))
    payload["error_by_time_bucket"] = grouped_error_report(
        time_frame,
        predicted_values,
        group_column="time_bucket",
        max_groups=8,
    )
    if lower is not None and upper is not None:
        payload["interval_coverage"] = interval_coverage(
            frame["actual_segment_minutes"], lower, upper
        )
    return payload
