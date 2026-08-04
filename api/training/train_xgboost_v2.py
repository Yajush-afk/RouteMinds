from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import sklearn
import xgboost
from xgboost import XGBRegressor

from api.common.features_v2 import (
    LIVE_DEFAULTS,
    LIVE_FEATURE_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    FeatureEncodingBundle,
)
from api.training.config import resolve_repo_path
from api.training.evaluation_v2 import complete_evaluation, trip_metrics
from api.training.schemas import ML_V2_SCHEMA_VERSION

DEFAULT_DATASET_DIR = "data/processed/ml/segments_v2"
DEFAULT_OUTPUT_ROOT = "artifacts/models/ml_v2"
DEFAULT_METRICS_ROOT = "artifacts/metrics/ml_v2"
DEFAULT_MANIFEST_ROOT = "artifacts/manifests"
DEFAULT_FEATURE_CACHE_ROOT = "data/processed/ml/features_v2"
DEFAULT_AUDIT_REVIEW_PATH = "artifacts/metrics/realtime_trace_audit_review_v2.json"
MINIMUM_FREE_DISK_GB = 10.0
TUNING_ROW_LIMIT = 1_000_000
TRAINING_COLUMNS = (
    "service_date",
    "source",
    "trip_id",
    "route_id",
    "from_stop_id",
    "to_stop_id",
    "stop_sequence",
    "scheduled_segment_minutes",
    "actual_segment_minutes",
    "slowdown_ratio",
    "log_slowdown_ratio",
    "distance_to_prev_stop_km",
    "segment_start_scheduled_unix",
    "sample_weight",
    "normalized_stop_position",
    "scheduled_headway_minutes",
    *LIVE_FEATURE_COLUMNS,
)
REQUIRED_TRAINING_COLUMNS = frozenset(TRAINING_COLUMNS[:15])


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    train_dates: tuple[str, ...]
    validation_dates: tuple[str, ...]
    test_dates: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the RouteMinds ML V2 XGBoost quantile bundle."
    )
    parser.add_argument("--dataset-dir", default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--metrics-root", default=DEFAULT_METRICS_ROOT)
    parser.add_argument("--manifest-root", default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument("--feature-cache-root", default=DEFAULT_FEATURE_CACHE_ROOT)
    parser.add_argument("--audit-review-path", default=DEFAULT_AUDIT_REVIEW_PATH)
    parser.add_argument("--model-version")
    parser.add_argument("--tuning-rows", type=int, default=TUNING_ROW_LIMIT)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def chronological_split(dataframe: pd.DataFrame) -> TemporalSplit:
    dates = sorted(str(value) for value in dataframe["service_date"].dropna().unique())
    if len(dates) < 3:
        raise ValueError("ML V2 chronological evaluation requires at least three service dates.")
    train_end = max(1, int(len(dates) * 0.70))
    validation_count = max(1, int(len(dates) * 0.15))
    validation_end = min(len(dates) - 1, train_end + validation_count)
    return TemporalSplit(
        train_dates=tuple(dates[:train_end]),
        validation_dates=tuple(dates[train_end:validation_end]),
        test_dates=tuple(dates[validation_end:]),
    )


def _parquet_files(dataset_dir: Path) -> list[Path]:
    files = sorted(dataset_dir.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No ML V2 Parquet files found under {dataset_dir}.")
    return files


def load_dataset(dataset_dir: str | Path, *, smoke: bool = False) -> pd.DataFrame:
    resolved = resolve_repo_path(str(dataset_dir))
    files = _parquet_files(resolved)
    frames: list[pd.DataFrame] = []
    row_budget = 60_000 if smoke else None
    for path in files:
        available_columns = set(pq.read_schema(path).names)
        missing_columns = REQUIRED_TRAINING_COLUMNS - available_columns
        if missing_columns:
            raise ValueError(
                f"ML V2 partition {path} is missing columns: "
                + ", ".join(sorted(missing_columns))
            )
        selected_columns = [
            column for column in TRAINING_COLUMNS if column in available_columns
        ]
        frame = pd.read_parquet(path, columns=selected_columns)
        frames.append(frame)
        if row_budget and sum(len(item) for item in frames) >= row_budget:
            break
    dataframe = pd.concat(frames, ignore_index=True)
    if row_budget:
        dataframe = dataframe.head(row_budget).copy()
    if len(dataframe) > 5_000_000:
        raise RuntimeError(
            "The canonical dataset exceeds five million rows. Materialize numeric feature "
            "partitions and use an external-memory QuantileDMatrix before training."
        )
    return dataframe.sort_values(
        ["service_date", "segment_start_scheduled_unix", "trip_id", "stop_sequence"]
    ).reset_index(drop=True)


def _dataset_hash(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path).encode("utf-8"))
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=resolve_repo_path("."), text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _model_parameters(config: dict[str, Any], *, smoke: bool) -> dict[str, Any]:
    return {
        "objective": "reg:squarederror",
        "tree_method": "hist",
        "device": "cpu",
        "n_jobs": min(12, os.cpu_count() or 1),
        "max_bin": 256,
        "n_estimators": 40 if smoke else 1200,
        "early_stopping_rounds": 5 if smoke else 50,
        "random_state": 42,
        **config,
    }


def _search_configs() -> list[dict[str, Any]]:
    return [
        {"max_depth": 4, "learning_rate": 0.05, "min_child_weight": 5, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1},
        {"max_depth": 6, "learning_rate": 0.05, "min_child_weight": 5, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 5},
        {"max_depth": 8, "learning_rate": 0.03, "min_child_weight": 20, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 10},
        {"max_depth": 4, "learning_rate": 0.08, "min_child_weight": 20, "subsample": 0.9, "colsample_bytree": 0.8, "reg_lambda": 5},
        {"max_depth": 6, "learning_rate": 0.03, "min_child_weight": 20, "subsample": 0.9, "colsample_bytree": 0.8, "reg_lambda": 10},
        {"max_depth": 8, "learning_rate": 0.05, "min_child_weight": 5, "subsample": 0.8, "colsample_bytree": 0.9, "reg_lambda": 5},
        {"max_depth": 4, "learning_rate": 0.03, "min_child_weight": 5, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 1},
        {"max_depth": 6, "learning_rate": 0.08, "min_child_weight": 20, "subsample": 0.8, "colsample_bytree": 0.9, "reg_lambda": 10},
        {"max_depth": 8, "learning_rate": 0.08, "min_child_weight": 20, "subsample": 0.9, "colsample_bytree": 0.8, "reg_lambda": 5},
        {"max_depth": 4, "learning_rate": 0.05, "min_child_weight": 20, "subsample": 0.8, "colsample_bytree": 0.9, "reg_lambda": 10},
        {"max_depth": 6, "learning_rate": 0.05, "min_child_weight": 5, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1},
        {"max_depth": 8, "learning_rate": 0.03, "min_child_weight": 5, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 10},
    ]


def _neutralize_live_features(features: pd.DataFrame) -> pd.DataFrame:
    cold = features.copy()
    for column, default in LIVE_DEFAULTS.items():
        cold[column] = default
    return cold


def _target(frame: pd.DataFrame, candidate: str) -> np.ndarray:
    if candidate == "absolute_duration":
        return frame["actual_segment_minutes"].to_numpy(dtype=float)
    if candidate == "residual_minutes":
        return (
            frame["actual_segment_minutes"] - frame["scheduled_segment_minutes"]
        ).to_numpy(dtype=float)
    return frame["log_slowdown_ratio"].to_numpy(dtype=float)


def _to_minutes(frame: pd.DataFrame, candidate: str, raw_predictions) -> np.ndarray:
    raw = np.asarray(raw_predictions, dtype=float)
    scheduled = frame["scheduled_segment_minutes"].to_numpy(dtype=float)
    if candidate == "absolute_duration":
        return np.clip(raw, 0.01, 120.0)
    if candidate == "residual_minutes":
        return np.clip(scheduled + raw, 0.01, 120.0)
    return np.clip(scheduled * np.exp(np.clip(raw, -4.0, 4.0)), 0.01, 120.0)


def _fit_regressor(
    x_train: pd.DataFrame,
    y_train,
    x_validation: pd.DataFrame,
    y_validation,
    sample_weight,
    parameters: dict[str, Any],
) -> XGBRegressor:
    model = XGBRegressor(**parameters)
    model.fit(
        x_train,
        y_train,
        sample_weight=sample_weight,
        eval_set=[(x_validation, y_validation)],
        verbose=False,
    )
    return model


def _calibration_scale(actual, p10, p50, p90, target: float = 0.8) -> float:
    actual = np.asarray(actual, dtype=float)
    p10 = np.asarray(p10, dtype=float)
    p50 = np.asarray(p50, dtype=float)
    p90 = np.asarray(p90, dtype=float)
    low, high = 0.25, 4.0
    for _ in range(30):
        scale = (low + high) / 2.0
        lower = p50 - (p50 - p10) * scale
        upper = p50 + (p90 - p50) * scale
        coverage = ((actual >= lower) & (actual <= upper)).mean()
        if coverage < target:
            low = scale
        else:
            high = scale
    return float((low + high) / 2.0)


def _predict_quantiles(
    models: dict[str, XGBRegressor],
    frame: pd.DataFrame,
    features: pd.DataFrame,
    calibration_scale: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw = {name: model.predict(features) for name, model in models.items()}
    values = {name: _to_minutes(frame, "log_slowdown", prediction) for name, prediction in raw.items()}
    ordered = np.sort(np.vstack([values["p10"], values["p50"], values["p90"]]), axis=0)
    p10, p50, p90 = ordered
    p10 = np.clip(p50 - (p50 - p10) * calibration_scale, 0.01, 120.0)
    p90 = np.clip(p50 + (p90 - p50) * calibration_scale, 0.01, 120.0)
    return p10, p50, p90


def _quantile_model_parameters(
    base: dict[str, Any], alpha: float, *, smoke: bool
) -> dict[str, Any]:
    parameters = _model_parameters(base, smoke=smoke)
    parameters.update(objective="reg:quantileerror", quantile_alpha=alpha)
    return parameters


def _manifest_metric_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "rows": metrics["rows"],
        "segment": metrics["segment"],
        "trip": metrics["trip"],
        "interval_coverage": metrics.get("interval_coverage"),
        "nonpositive_prediction_count": metrics["nonpositive_prediction_count"],
        "fallback_rate": metrics.get("fallback_rate", 0.0),
    }


def _materialize_numeric_features(
    directory: Path,
    splits: tuple[tuple[str, pd.DataFrame, pd.DataFrame], ...],
) -> dict[str, str]:
    if directory.exists():
        raise FileExistsError(f"ML V2 feature cache already exists: {directory}")
    directory.mkdir(parents=True)
    paths: dict[str, str] = {}
    for name, frame, features in splits:
        materialized = features.reset_index(drop=True).copy()
        for column in (
            "scheduled_segment_minutes",
            "actual_segment_minutes",
            "log_slowdown_ratio",
            "sample_weight",
        ):
            materialized[f"target__{column}"] = pd.to_numeric(
                frame[column], errors="raise"
            ).to_numpy(dtype="float32")
        path = directory / f"{name}.parquet"
        materialized.astype("float32").to_parquet(path, index=False)
        paths[name] = str(path)
    return paths


def _load_audit_review(path: str | Path) -> tuple[dict[str, Any] | None, list[str]]:
    resolved = resolve_repo_path(str(path))
    if not resolved.exists():
        return None, ["The manually reviewed 200-trace realtime audit is missing."]
    try:
        review = json.loads(resolved.read_text(encoding="utf-8"))
        reviewed = int(review["reviewed_trace_count"])
        route_accuracy = float(review["route_direction_accuracy"])
        monotonic_rate = float(review["monotonic_progression_rate"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return None, [f"The realtime audit review is invalid: {exc}."]

    blockers: list[str] = []
    if reviewed < 200:
        blockers.append("Fewer than 200 realtime traces were manually reviewed.")
    if route_accuracy < 0.90:
        blockers.append("Realtime audit route/direction accuracy is below 90%.")
    if monotonic_rate < 0.95:
        blockers.append("Realtime audit monotonic progression is below 95%.")
    return review, blockers


def train_v2(
    *,
    dataset_dir: str | Path = DEFAULT_DATASET_DIR,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    metrics_root: str | Path = DEFAULT_METRICS_ROOT,
    manifest_root: str | Path = DEFAULT_MANIFEST_ROOT,
    feature_cache_root: str | Path = DEFAULT_FEATURE_CACHE_ROOT,
    audit_review_path: str | Path = DEFAULT_AUDIT_REVIEW_PATH,
    model_version: str | None = None,
    tuning_rows: int = TUNING_ROW_LIMIT,
    smoke: bool = False,
) -> dict[str, Any]:
    version = model_version or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root_path = resolve_repo_path(str(output_root))
    model_dir = output_root_path / version
    if model_dir.exists():
        raise FileExistsError(f"ML V2 model version already exists: {model_dir}")
    free_gb = shutil.disk_usage(output_root_path.parent).free / (1024**3)
    if free_gb < MINIMUM_FREE_DISK_GB:
        raise RuntimeError(f"Only {free_gb:.1f} GiB free; ML V2 training requires 10 GiB.")

    dataset = load_dataset(dataset_dir, smoke=smoke)
    split = chronological_split(dataset)
    train_frame = dataset[dataset["service_date"].astype(str).isin(split.train_dates)].copy()
    validation_frame = dataset[
        dataset["service_date"].astype(str).isin(split.validation_dates)
    ].copy()
    test_frame = dataset[dataset["service_date"].astype(str).isin(split.test_dates)].copy()

    bundle = FeatureEncodingBundle(smoothing=50.0)
    x_train = bundle.fit_transform_oof(train_frame, folds=5)
    x_validation = bundle.transform(validation_frame)
    x_test = bundle.transform(test_frame)
    feature_cache_dir = resolve_repo_path(str(feature_cache_root)) / version
    feature_cache_paths = _materialize_numeric_features(
        feature_cache_dir,
        (
            ("train", train_frame, x_train),
            ("validation", validation_frame, x_validation),
            ("test", test_frame, x_test),
        ),
    )
    sample_weight = train_frame["sample_weight"].to_numpy(dtype=float)

    tuning_limit = min(len(train_frame), tuning_rows, 50_000 if smoke else tuning_rows)
    tuning_positions = np.linspace(0, len(train_frame) - 1, tuning_limit, dtype=int)
    search_results: list[dict[str, Any]] = []
    configs = _search_configs()[:1] if smoke else _search_configs()
    for config in configs:
        parameters = _model_parameters(config, smoke=smoke)
        model = _fit_regressor(
            x_train.iloc[tuning_positions],
            _target(train_frame.iloc[tuning_positions], "log_slowdown"),
            x_validation,
            _target(validation_frame, "log_slowdown"),
            sample_weight[tuning_positions],
            parameters,
        )
        predictions = _to_minutes(
            validation_frame, "log_slowdown", model.predict(x_validation)
        )
        search_results.append(
            {
                "config": config,
                "best_iteration": int(model.best_iteration),
                "validation_trip": trip_metrics(validation_frame, predictions),
            }
        )
    search_results.sort(key=lambda result: result["validation_trip"]["mae"])

    finalist_results: list[dict[str, Any]] = []
    selected_config = search_results[0]["config"]
    for result in search_results[: min(3, len(search_results))]:
        config = result["config"]
        model = _fit_regressor(
            x_train,
            _target(train_frame, "log_slowdown"),
            x_validation,
            _target(validation_frame, "log_slowdown"),
            sample_weight,
            _model_parameters(config, smoke=smoke),
        )
        predictions = _to_minutes(
            validation_frame, "log_slowdown", model.predict(x_validation)
        )
        finalist_results.append(
            {
                "config": config,
                "best_iteration": int(model.best_iteration),
                "validation_trip": trip_metrics(validation_frame, predictions),
            }
        )
    finalist_results.sort(key=lambda result: result["validation_trip"]["mae"])
    selected_config = finalist_results[0]["config"]

    candidate_results: dict[str, Any] = {}
    for candidate in ("absolute_duration", "residual_minutes", "log_slowdown", "log_slowdown_live"):
        use_live = candidate == "log_slowdown_live"
        candidate_name = "log_slowdown" if candidate == "log_slowdown_live" else candidate
        train_features = x_train if use_live else _neutralize_live_features(x_train)
        validation_features = x_validation if use_live else _neutralize_live_features(x_validation)
        model = _fit_regressor(
            train_features,
            _target(train_frame, candidate_name),
            validation_features,
            _target(validation_frame, candidate_name),
            sample_weight,
            _model_parameters(selected_config, smoke=smoke),
        )
        predictions = _to_minutes(
            validation_frame,
            candidate_name,
            model.predict(validation_features),
        )
        candidate_results[candidate] = complete_evaluation(validation_frame, predictions)

    quantile_models: dict[str, XGBRegressor] = {}
    for name, alpha in (("p10", 0.10), ("p50", 0.50), ("p90", 0.90)):
        quantile_models[name] = _fit_regressor(
            x_train,
            _target(train_frame, "log_slowdown"),
            x_validation,
            _target(validation_frame, "log_slowdown"),
            sample_weight,
            _quantile_model_parameters(selected_config, alpha, smoke=smoke),
        )

    uncalibrated = _predict_quantiles(
        quantile_models, validation_frame, x_validation, calibration_scale=1.0
    )
    calibration_scale = _calibration_scale(
        validation_frame["actual_segment_minutes"], *uncalibrated
    )
    validation_quantiles = _predict_quantiles(
        quantile_models, validation_frame, x_validation, calibration_scale
    )
    test_quantiles = _predict_quantiles(
        quantile_models, test_frame, x_test, calibration_scale
    )

    schedule_test = test_frame["scheduled_segment_minutes"].to_numpy(dtype=float)
    historical_test = np.clip(
        schedule_test * x_test["edge_time_median_slowdown"].to_numpy(dtype=float),
        0.01,
        120.0,
    )
    static_test_metrics = complete_evaluation(test_frame, schedule_test)
    static_test_metrics["fallback_rate"] = 1.0
    test_metrics = {
        "static_schedule": static_test_metrics,
        "historical_edge_time": complete_evaluation(test_frame, historical_test),
        "ml_v2": complete_evaluation(
            test_frame,
            test_quantiles[1],
            lower=test_quantiles[0],
            upper=test_quantiles[2],
        ),
    }
    source_metrics: dict[str, Any] = {}
    for source, source_frame in test_frame.groupby("source", sort=True):
        positions = test_frame.index.get_indexer(source_frame.index)
        source_metrics[str(source)] = complete_evaluation(
            source_frame,
            test_quantiles[1][positions],
            lower=test_quantiles[0][positions],
            upper=test_quantiles[2][positions],
        )

    cold_test = _neutralize_live_features(x_test)
    cold_quantiles = _predict_quantiles(
        quantile_models, test_frame, cold_test, calibration_scale
    )
    test_metrics["cold_start"] = complete_evaluation(test_frame, cold_quantiles[1])
    live_mask = test_frame.get("live_context_available", pd.Series(0, index=test_frame.index)) > 0
    test_metrics["live_context"] = (
        complete_evaluation(test_frame[live_mask], test_quantiles[1][live_mask.to_numpy()])
        if live_mask.any()
        else {"rows": 0, "status": "no_live_context_rows"}
    )

    batch = x_test.head(min(256, len(x_test)))
    latency_samples: list[float] = []
    for _ in range(20):
        started = time.perf_counter()
        quantile_models["p50"].predict(batch)
        latency_samples.append((time.perf_counter() - started) * 1000.0)
    latency_p95 = float(np.quantile(latency_samples, 0.95))

    model_dir.mkdir(parents=True)
    for name, model in quantile_models.items():
        model.save_model(model_dir / f"{name}_model.json")
    feature_paths = bundle.save(model_dir)

    real_all = dataset[dataset["source"] == "realtime"]
    real_test = test_frame[test_frame["source"] == "realtime"]
    promotion_reasons: list[str] = []
    audit_review, audit_blockers = _load_audit_review(audit_review_path)
    promotion_reasons.extend(audit_blockers)
    if len(real_all) < 10_000 or real_all["service_date"].nunique() < 7:
        promotion_reasons.append(
            "Fewer than 10,000 high-confidence realtime segments across seven service dates."
        )
    if real_test["service_date"].nunique() < 3 or real_test.empty:
        promotion_reasons.append("Realtime test metrics cover fewer than three held-out dates.")
    else:
        positions = test_frame.index.get_indexer(real_test.index)
        real_ml = complete_evaluation(real_test, test_quantiles[1][positions])
        real_schedule = complete_evaluation(
            real_test, real_test["scheduled_segment_minutes"]
        )
        if real_ml["trip"]["mae"] > real_schedule["trip"]["mae"] * 0.9:
            promotion_reasons.append("Realtime trip MAE did not beat schedule by 10%.")
        if real_ml["trip"]["p90_absolute_error"] > (
            real_schedule["trip"]["p90_absolute_error"] * 1.05
        ):
            promotion_reasons.append("Realtime trip P90 error is over 5% worse than schedule.")
        real_cold = complete_evaluation(real_test, cold_quantiles[1][positions])
        if real_cold["trip"]["mae"] > real_schedule["trip"]["mae"]:
            promotion_reasons.append("Realtime cold-start MAE is worse than schedule.")
    interval_coverage = float(test_metrics["ml_v2"].get("interval_coverage", 0.0))
    if not 0.75 <= interval_coverage <= 0.85:
        promotion_reasons.append("P10-P90 coverage is outside 75-85%.")
    if test_metrics["ml_v2"]["nonpositive_prediction_count"]:
        promotion_reasons.append("Model produced nonpositive predictions.")
    if latency_p95 >= 100.0:
        promotion_reasons.append("Batch-256 p95 inference latency exceeds 100 ms.")

    artifact_paths = [
        model_dir / "p10_model.json",
        model_dir / "p50_model.json",
        model_dir / "p90_model.json",
        Path(feature_paths["feature_schema"]),
        Path(feature_paths["category_encodings"]),
        Path(feature_paths["historical_features"]),
    ]
    artifact_checksums = {path.name: _sha256(path) for path in artifact_paths}
    dataset_path = resolve_repo_path(str(dataset_dir))
    manifest: dict[str, Any] = {
        "model_version": version,
        "schema_version": ML_V2_SCHEMA_VERSION,
        "training_git_commit": _git_commit(),
        "dataset_hash": _dataset_hash(_parquet_files(dataset_path)),
        "training_date_range": [split.train_dates[0], split.train_dates[-1]],
        "validation_dates": list(split.validation_dates),
        "test_dates": list(split.test_dates),
        "package_versions": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
        },
        "target_definition": "log(actual_segment_minutes / scheduled_segment_minutes)",
        "feature_cache": feature_cache_paths,
        "feature_order": list(MODEL_FEATURE_COLUMNS),
        "selected_parameters": selected_config,
        "training_parameters": _model_parameters(selected_config, smoke=smoke),
        "calibration_scale": calibration_scale,
        "nominal_interval_coverage": 0.8,
        "artifact_checksums": artifact_checksums,
        "supported_routes": int(train_frame["route_id"].nunique()),
        "supported_edges": int(
            train_frame[["route_id", "from_stop_id", "to_stop_id"]]
            .drop_duplicates()
            .shape[0]
        ),
        "baseline_metrics": {
            "static_schedule": _manifest_metric_summary(test_metrics["static_schedule"]),
            "historical_edge_time": _manifest_metric_summary(
                test_metrics["historical_edge_time"]
            ),
        },
        "validation_metrics": _manifest_metric_summary(
            complete_evaluation(
                validation_frame,
                validation_quantiles[1],
                lower=validation_quantiles[0],
                upper=validation_quantiles[2],
            )
        ),
        "test_metrics": _manifest_metric_summary(test_metrics["ml_v2"]),
        "realtime_audit_review": audit_review,
        "promotion_eligible": not promotion_reasons,
        "promotion_blockers": promotion_reasons,
    }
    (model_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    metrics = {
        "model_version": version,
        "rows": {
            "train": len(train_frame),
            "validation": len(validation_frame),
            "test": len(test_frame),
        },
        "split": {
            "train_dates": list(split.train_dates),
            "validation_dates": list(split.validation_dates),
            "test_dates": list(split.test_dates),
        },
        "search_results": search_results,
        "finalist_results": finalist_results,
        "candidate_validation": candidate_results,
        "validation": complete_evaluation(
            validation_frame,
            validation_quantiles[1],
            lower=validation_quantiles[0],
            upper=validation_quantiles[2],
        ),
        "test": test_metrics,
        "test_by_source": source_metrics,
        "calibration_scale": calibration_scale,
        "batch_256_latency_ms": {
            "p50": float(np.median(latency_samples)),
            "p95": latency_p95,
        },
        "promotion_eligible": not promotion_reasons,
        "promotion_blockers": promotion_reasons,
    }
    metrics_dir = resolve_repo_path(str(metrics_root))
    metrics_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = metrics_dir / f"{version}.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    tracked_manifest_dir = resolve_repo_path(str(manifest_root))
    tracked_manifest_dir.mkdir(parents=True, exist_ok=True)
    tracked_manifest = {**manifest, "model_directory": str(model_dir), "metrics_path": str(metrics_path)}
    (tracked_manifest_dir / f"{version}.json").write_text(
        json.dumps(tracked_manifest, indent=2), encoding="utf-8"
    )
    return {"manifest": manifest, "metrics": metrics, "model_directory": str(model_dir)}


def main() -> None:
    args = parse_args()
    result = train_v2(
        dataset_dir=args.dataset_dir,
        output_root=args.output_root,
        metrics_root=args.metrics_root,
        manifest_root=args.manifest_root,
        feature_cache_root=args.feature_cache_root,
        audit_review_path=args.audit_review_path,
        model_version=args.model_version,
        tuning_rows=args.tuning_rows,
        smoke=args.smoke,
    )
    print(
        json.dumps(
            {
                "model_directory": result["model_directory"],
                "model_version": result["manifest"]["model_version"],
                "promotion_eligible": result["manifest"]["promotion_eligible"],
                "promotion_blockers": result["manifest"]["promotion_blockers"],
                "test_segment_mae": result["metrics"]["test"]["ml_v2"]["segment"]["mae"],
                "test_trip_mae": result["metrics"]["test"]["ml_v2"]["trip"]["mae"],
                "interval_coverage": result["metrics"]["test"]["ml_v2"]["interval_coverage"],
                "batch_256_latency_p95_ms": result["metrics"]["batch_256_latency_ms"]["p95"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
