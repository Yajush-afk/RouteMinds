from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from xgboost import XGBRegressor

from api.training.config import (
    FeatureConfig,
    TrainingConfig,
    load_training_config,
    resolve_repo_path,
    serialize_training_config,
)
from api.training.data import (
    annotate_trip_start,
    derive_segment_dataset,
    load_dataset,
    split_dataset,
    take_group_row_budget,
)
from api.training.features import build_training_frame

DEFAULT_CONFIG_PATH = "api/training/config/default_config.toml"


@dataclass(slots=True)
class ExperimentResult:
    target_column: str
    feature_config: FeatureConfig
    pipeline: Pipeline
    train_rows: int
    validation_rows: int
    test_rows: int
    validation_metrics: dict[str, float]
    test_metrics: dict[str, float]
    secondary_target_column: str | None = None
    validation_secondary_metrics: dict[str, float] | None = None
    test_secondary_metrics: dict[str, float] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the RouteMinds XGBoost segment travel-time baseline."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to the training TOML config, relative to api/ or repo root.",
    )
    return parser.parse_args()


def build_experiment_pipeline(
    config: TrainingConfig, feature_config: FeatureConfig
) -> Pipeline:
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                    encoded_missing_value=-1,
                ),
            ),
        ]
    )

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", categorical_transformer, feature_config.categorical),
            ("numeric", numeric_transformer, feature_config.numeric),
        ],
        remainder="drop",
    )

    regressor = XGBRegressor(
        objective="reg:squarederror",
        tree_method="hist",
        n_estimators=config.model.n_estimators,
        max_depth=config.model.max_depth,
        learning_rate=config.model.learning_rate,
        subsample=config.model.subsample,
        colsample_bytree=config.model.colsample_bytree,
        reg_alpha=config.model.reg_alpha,
        reg_lambda=config.model.reg_lambda,
        random_state=config.model.random_state,
        n_jobs=-1,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", regressor),
        ]
    )


def regression_metrics(target: pd.Series, predictions) -> dict[str, float]:
    rmse = root_mean_squared_error(target, predictions)
    return {
        "mae": float(mean_absolute_error(target, predictions)),
        "rmse": float(rmse),
        "r2": float(r2_score(target, predictions)),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def prepare_datasets(config: TrainingConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw_dataframe = load_dataset(config)
    stop_smoke_dataframe = annotate_trip_start(raw_dataframe, config)
    segment_dataframe = derive_segment_dataset(raw_dataframe, config)
    return raw_dataframe, stop_smoke_dataframe, segment_dataframe


def run_experiment(
    dataframe: pd.DataFrame,
    config: TrainingConfig,
    feature_config: FeatureConfig,
    target_column: str,
    secondary_target_column: str | None = None,
) -> ExperimentResult:
    train_frame, validation_frame, test_frame = split_dataset(dataframe, config)

    x_train, y_train = build_training_frame(train_frame, feature_config, target_column)
    x_validation, y_validation = build_training_frame(
        validation_frame, feature_config, target_column
    )
    x_test, y_test = build_training_frame(test_frame, feature_config, target_column)

    pipeline = build_experiment_pipeline(config, feature_config)
    pipeline.fit(x_train, y_train)

    validation_predictions = pipeline.predict(x_validation)
    test_predictions = pipeline.predict(x_test)

    validation_metrics = regression_metrics(y_validation, validation_predictions)
    test_metrics = regression_metrics(y_test, test_predictions)

    validation_secondary_metrics = None
    test_secondary_metrics = None
    if secondary_target_column:
        if secondary_target_column not in validation_frame.columns:
            raise ValueError(
                f"Secondary target column '{secondary_target_column}' is missing."
            )
        validation_secondary_metrics = regression_metrics(
            validation_frame.loc[x_validation.index, secondary_target_column],
            validation_predictions - x_validation["scheduled_segment_minutes"],
        )
        test_secondary_metrics = regression_metrics(
            test_frame.loc[x_test.index, secondary_target_column],
            test_predictions - x_test["scheduled_segment_minutes"],
        )

    return ExperimentResult(
        target_column=target_column,
        feature_config=feature_config,
        pipeline=pipeline,
        train_rows=int(len(x_train)),
        validation_rows=int(len(x_validation)),
        test_rows=int(len(x_test)),
        validation_metrics=validation_metrics,
        test_metrics=test_metrics,
        secondary_target_column=secondary_target_column,
        validation_secondary_metrics=validation_secondary_metrics,
        test_secondary_metrics=test_secondary_metrics,
    )


def save_experiment_artifacts(
    config: TrainingConfig,
    raw_dataframe: pd.DataFrame,
    segment_dataframe: pd.DataFrame,
    canonical_result: ExperimentResult,
    smoke_result: ExperimentResult | None,
) -> None:
    model_path = resolve_repo_path(config.artifacts.model_path)
    schema_path = resolve_repo_path(config.artifacts.schema_path)
    metrics_path = resolve_repo_path(config.artifacts.metrics_path)
    config_snapshot_path = resolve_repo_path(config.artifacts.config_snapshot_path)
    smoke_metrics_path = resolve_repo_path(config.artifacts.smoke_metrics_path)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(canonical_result.pipeline, model_path)

    schema_payload = {
        "derivation_mode": "segment",
        "target_column": canonical_result.target_column,
        "secondary_target_column": canonical_result.secondary_target_column,
        "categorical_features": canonical_result.feature_config.categorical,
        "numeric_features": canonical_result.feature_config.numeric,
        "drop_columns": canonical_result.feature_config.drop,
        "feature_time_column": canonical_result.feature_config.feature_time_column,
        "group_by": config.split.group_by,
        "sort_by": config.split.sort_by,
    }
    write_json(schema_path, schema_payload)

    metrics_payload: dict[str, Any] = {
        "dataset_path": str(resolve_repo_path(config.data.dataset_path)),
        "raw_row_count": int(len(raw_dataframe)),
        "segment_row_count": int(len(segment_dataframe)),
        "train_rows": canonical_result.train_rows,
        "validation_rows": canonical_result.validation_rows,
        "test_rows": canonical_result.test_rows,
        "split_policy": {
            "group_by": config.split.group_by,
            "sort_by": config.split.sort_by,
            "train_fraction": config.split.train_fraction,
            "validation_fraction": config.split.validation_fraction,
            "test_fraction": config.split.test_fraction,
        },
        "canonical_target": {
            "name": canonical_result.target_column,
            "validation": canonical_result.validation_metrics,
            "test": canonical_result.test_metrics,
        },
    }
    if canonical_result.secondary_target_column:
        metrics_payload["secondary_target"] = {
            "name": canonical_result.secondary_target_column,
            "validation": canonical_result.validation_secondary_metrics,
            "test": canonical_result.test_secondary_metrics,
        }
    write_json(metrics_path, metrics_payload)

    if smoke_result:
        smoke_payload = {
            "dataset_path": str(resolve_repo_path(config.data.dataset_path)),
            "target_column": smoke_result.target_column,
            "sample_rows": config.smoke.sample_rows,
            "train_rows": smoke_result.train_rows,
            "validation_rows": smoke_result.validation_rows,
            "test_rows": smoke_result.test_rows,
            "validation": smoke_result.validation_metrics,
            "test": smoke_result.test_metrics,
        }
        write_json(smoke_metrics_path, smoke_payload)

    write_json(config_snapshot_path, serialize_training_config(config))


def train(config: TrainingConfig) -> dict[str, ExperimentResult | None]:
    raw_dataframe, stop_smoke_dataframe, segment_dataframe = prepare_datasets(config)

    smoke_result = None
    if config.smoke.enabled:
        smoke_frame = take_group_row_budget(
            stop_smoke_dataframe,
            config.split.group_by,
            "trip_start_scheduled_unix",
            config.smoke.sample_rows,
        )
        smoke_result = run_experiment(
            smoke_frame,
            config,
            config.stop_smoke_features,
            config.targets.smoke_target,
        )

    canonical_result = run_experiment(
        segment_dataframe,
        config,
        config.segment_features,
        config.targets.canonical_target,
        secondary_target_column=config.targets.secondary_target,
    )

    save_experiment_artifacts(
        config,
        raw_dataframe=raw_dataframe,
        segment_dataframe=segment_dataframe,
        canonical_result=canonical_result,
        smoke_result=smoke_result,
    )

    print("Training finished.")
    print(f"Saved model: {resolve_repo_path(config.artifacts.model_path)}")
    print(f"Saved schema: {resolve_repo_path(config.artifacts.schema_path)}")
    print(f"Saved metrics: {resolve_repo_path(config.artifacts.metrics_path)}")
    print(
        "Canonical validation MAE: "
        f"{canonical_result.validation_metrics['mae']:.4f}"
    )
    print(f"Canonical test MAE: {canonical_result.test_metrics['mae']:.4f}")
    if canonical_result.validation_secondary_metrics:
        print(
            "Canonical validation segment-delay MAE: "
            f"{canonical_result.validation_secondary_metrics['mae']:.4f}"
        )
    if smoke_result:
        print(f"Smoke validation MAE: {smoke_result.validation_metrics['mae']:.4f}")

    return {
        "smoke": smoke_result,
        "canonical": canonical_result,
    }


def main() -> None:
    args = parse_args()
    config = load_training_config(args.config)
    train(config)


if __name__ == "__main__":
    main()
