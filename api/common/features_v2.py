from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from api.training.schemas import LIVE_FEATURE_COLUMNS, ML_V2_SCHEMA_VERSION

TARGET_COLUMN = "log_slowdown_ratio"
CATEGORY_COLUMNS = ("route_id", "from_stop_id", "to_stop_id", "edge_key")

MODEL_FEATURE_COLUMNS = (
    "scheduled_segment_minutes",
    "log_scheduled_segment_minutes",
    "distance_to_prev_stop_km",
    "stop_sequence",
    "normalized_stop_position",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "is_weekend",
    "is_morning_peak",
    "is_evening_peak",
    "scheduled_headway_minutes",
    "route_frequency",
    "edge_frequency",
    "route_target_encoding",
    "edge_target_encoding",
    "from_stop_target_encoding",
    "to_stop_target_encoding",
    "edge_time_median_slowdown",
    "edge_time_p75_slowdown",
    "route_time_median_slowdown",
    "edge_variability",
    "historical_sample_count",
    *LIVE_FEATURE_COLUMNS,
)

LIVE_DEFAULTS: dict[str, float] = {
    "prev_segment_delay": 0.0,
    "rolling_segment_delay_3": 0.0,
    "route_delay_minutes_live": 0.0,
    "segment_slowdown_index": 1.0,
    "corridor_slowdown_score_live": 1.0,
    "headway_irregularity_score_live": 0.0,
    "bunching_indicator": 0.0,
    "live_context_age_seconds": 0.0,
    "live_context_observation_count": 0.0,
    "live_context_available": 0.0,
}


def _normalize_identifier(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    normalized = str(value).strip()
    if normalized.endswith(".0"):
        prefix = normalized[:-2]
        if prefix.lstrip("-").isdigit():
            return prefix
    return normalized


def _prepare_keys(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    for column in ("route_id", "from_stop_id", "to_stop_id"):
        if column not in prepared.columns:
            raise ValueError(f"ML V2 feature frame is missing: {column}.")
        prepared[column] = prepared[column].map(_normalize_identifier)
    prepared["edge_key"] = (
        prepared["route_id"]
        + "\x1f"
        + prepared["from_stop_id"]
        + "\x1f"
        + prepared["to_stop_id"]
    )
    return prepared


def _time_features(frame: pd.DataFrame) -> pd.DataFrame:
    timestamps = pd.to_datetime(
        pd.to_numeric(frame["segment_start_scheduled_unix"], errors="coerce"),
        unit="s",
        utc=True,
        errors="coerce",
    ).dt.tz_convert("Asia/Kolkata")
    hour = timestamps.dt.hour + timestamps.dt.minute / 60.0
    day = timestamps.dt.dayofweek
    result = pd.DataFrame(index=frame.index)
    result["hour_sin"] = np.sin(2.0 * math.pi * hour / 24.0)
    result["hour_cos"] = np.cos(2.0 * math.pi * hour / 24.0)
    result["day_of_week_sin"] = np.sin(2.0 * math.pi * day / 7.0)
    result["day_of_week_cos"] = np.cos(2.0 * math.pi * day / 7.0)
    result["is_weekend"] = (day >= 5).astype(float)
    result["is_morning_peak"] = ((hour >= 7.0) & (hour < 10.0)).astype(float)
    result["is_evening_peak"] = ((hour >= 16.0) & (hour < 20.0)).astype(float)
    result["time_bucket"] = (timestamps.dt.hour * 2 + timestamps.dt.minute // 30).fillna(0)
    return result


@dataclass(slots=True)
class FeatureEncodingBundle:
    smoothing: float = 50.0
    global_target_mean: float = 0.0
    category_encodings: pd.DataFrame = field(default_factory=pd.DataFrame)
    edge_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    route_history: pd.DataFrame = field(default_factory=pd.DataFrame)

    def fit(self, dataframe: pd.DataFrame) -> "FeatureEncodingBundle":
        frame = _prepare_keys(dataframe)
        if TARGET_COLUMN not in frame.columns:
            raise ValueError(f"Training frame is missing target column: {TARGET_COLUMN}.")
        target = pd.to_numeric(frame[TARGET_COLUMN], errors="raise")
        self.global_target_mean = float(target.mean()) if len(target) else 0.0

        encoding_frames: list[pd.DataFrame] = []
        output_names = {
            "route_id": "route",
            "from_stop_id": "from_stop",
            "to_stop_id": "to_stop",
            "edge_key": "edge",
        }
        for column, feature_name in output_names.items():
            grouped = (
                frame.assign(_target=target)
                .groupby(column, sort=False)["_target"]
                .agg(["mean", "count"])
                .reset_index()
                .rename(columns={column: "key"})
            )
            grouped["target_encoding"] = (
                grouped["mean"] * grouped["count"]
                + self.global_target_mean * self.smoothing
            ) / (grouped["count"] + self.smoothing)
            grouped["frequency"] = np.log1p(grouped["count"])
            grouped["feature"] = feature_name
            encoding_frames.append(
                grouped[["feature", "key", "target_encoding", "frequency", "count"]]
            )
        self.category_encodings = pd.concat(encoding_frames, ignore_index=True)

        temporal = _time_features(frame)
        history_frame = frame.assign(
            _slowdown=pd.to_numeric(frame["slowdown_ratio"], errors="raise"),
            _time_bucket=temporal["time_bucket"].astype(int),
        )
        self.edge_history = (
            history_frame.groupby(["edge_key", "_time_bucket"], sort=False)["_slowdown"]
            .agg(
                edge_time_median_slowdown="median",
                edge_time_p75_slowdown=lambda values: values.quantile(0.75),
                edge_variability="std",
                historical_sample_count="count",
            )
            .reset_index()
            .rename(columns={"_time_bucket": "time_bucket"})
        )
        self.edge_history["edge_variability"] = self.edge_history[
            "edge_variability"
        ].fillna(0.0)
        self.route_history = (
            history_frame.groupby(["route_id", "_time_bucket"], sort=False)["_slowdown"]
            .median()
            .rename("route_time_median_slowdown")
            .reset_index()
            .rename(columns={"_time_bucket": "time_bucket"})
        )
        return self

    def _category_lookup(self, feature: str) -> pd.DataFrame:
        selected = self.category_encodings[
            self.category_encodings["feature"] == feature
        ].copy()
        return selected.set_index("key")

    def transform(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        frame = _prepare_keys(dataframe)
        temporal = _time_features(frame)
        features = pd.DataFrame(index=frame.index)

        scheduled = pd.to_numeric(frame["scheduled_segment_minutes"], errors="coerce")
        features["scheduled_segment_minutes"] = scheduled
        features["log_scheduled_segment_minutes"] = np.log(scheduled.clip(lower=0.01))
        for column in (
            "distance_to_prev_stop_km",
            "stop_sequence",
            "normalized_stop_position",
        ):
            features[column] = pd.to_numeric(frame[column], errors="coerce")
        for column in (
            "hour_sin",
            "hour_cos",
            "day_of_week_sin",
            "day_of_week_cos",
            "is_weekend",
            "is_morning_peak",
            "is_evening_peak",
        ):
            features[column] = temporal[column]
        features["scheduled_headway_minutes"] = pd.to_numeric(
            frame.get("scheduled_headway_minutes", 0.0), errors="coerce"
        )

        category_specs = (
            ("route_id", "route", "route_target_encoding", "route_frequency"),
            ("edge_key", "edge", "edge_target_encoding", "edge_frequency"),
            ("from_stop_id", "from_stop", "from_stop_target_encoding", None),
            ("to_stop_id", "to_stop", "to_stop_target_encoding", None),
        )
        for key_column, feature, target_column, frequency_column in category_specs:
            lookup = self._category_lookup(feature)
            features[target_column] = frame[key_column].map(lookup["target_encoding"])
            if frequency_column:
                features[frequency_column] = frame[key_column].map(lookup["frequency"])

        history_keys = pd.DataFrame(
            {
                "edge_key": frame["edge_key"],
                "route_id": frame["route_id"],
                "time_bucket": temporal["time_bucket"].astype(int),
                "_row_order": np.arange(len(frame)),
            },
            index=frame.index,
        )
        edge_join = history_keys.reset_index(drop=True).merge(
            self.edge_history,
            on=["edge_key", "time_bucket"],
            how="left",
            sort=False,
        ).sort_values("_row_order")
        route_join = history_keys.reset_index(drop=True).merge(
            self.route_history,
            on=["route_id", "time_bucket"],
            how="left",
            sort=False,
        ).sort_values("_row_order")
        features["edge_time_median_slowdown"] = edge_join[
            "edge_time_median_slowdown"
        ].to_numpy()
        features["edge_time_p75_slowdown"] = edge_join[
            "edge_time_p75_slowdown"
        ].to_numpy()
        features["edge_variability"] = edge_join["edge_variability"].to_numpy()
        features["historical_sample_count"] = edge_join[
            "historical_sample_count"
        ].to_numpy()
        features["route_time_median_slowdown"] = route_join[
            "route_time_median_slowdown"
        ].to_numpy()

        for column, default in LIVE_DEFAULTS.items():
            value = frame[column] if column in frame.columns else default
            features[column] = pd.to_numeric(value, errors="coerce")

        fallback_values = {
            "route_frequency": 0.0,
            "edge_frequency": 0.0,
            "route_target_encoding": self.global_target_mean,
            "edge_target_encoding": self.global_target_mean,
            "from_stop_target_encoding": self.global_target_mean,
            "to_stop_target_encoding": self.global_target_mean,
            "edge_time_median_slowdown": 1.0,
            "edge_time_p75_slowdown": 1.0,
            "route_time_median_slowdown": 1.0,
            "edge_variability": 0.0,
            "historical_sample_count": 0.0,
            "scheduled_headway_minutes": 0.0,
            **LIVE_DEFAULTS,
        }
        features = features.replace([np.inf, -np.inf], np.nan).fillna(fallback_values)
        features = features.fillna(0.0)
        return features[list(MODEL_FEATURE_COLUMNS)].astype("float32")

    def fit_transform_oof(
        self,
        dataframe: pd.DataFrame,
        *,
        folds: int = 5,
    ) -> pd.DataFrame:
        if folds < 2:
            raise ValueError("OOF feature generation requires at least two folds.")
        ordered = dataframe.sort_values(
            ["service_date", "segment_start_scheduled_unix", "trip_id", "stop_sequence"]
        )
        fold_indices = np.array_split(np.arange(len(ordered)), folds)
        transformed_parts: list[pd.DataFrame] = []
        for fold_number, positions in enumerate(fold_indices):
            if not len(positions):
                continue
            fold_frame = ordered.iloc[positions]
            prior_positions = np.concatenate(fold_indices[:fold_number]) if fold_number else []
            if len(prior_positions):
                fold_bundle = FeatureEncodingBundle(smoothing=self.smoothing).fit(
                    ordered.iloc[prior_positions]
                )
            else:
                neutral = fold_frame.head(1).copy()
                neutral[TARGET_COLUMN] = 0.0
                neutral["slowdown_ratio"] = 1.0
                fold_bundle = FeatureEncodingBundle(smoothing=self.smoothing).fit(neutral)
            transformed = fold_bundle.transform(fold_frame)
            transformed.index = fold_frame.index
            transformed_parts.append(transformed)

        self.fit(ordered)
        result = pd.concat(transformed_parts).loc[dataframe.index]
        return result

    def save(self, directory: str | Path) -> dict[str, str]:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        category_path = target / "category_encodings.parquet"
        history_path = target / "historical_features.parquet"
        schema_path = target / "feature_schema.json"
        self.category_encodings.to_parquet(category_path, index=False)
        edge_history = self.edge_history.assign(history_type="edge")
        route_history = self.route_history.assign(history_type="route")
        pd.concat([edge_history, route_history], ignore_index=True, sort=False).to_parquet(
            history_path, index=False
        )
        schema_path.write_text(
            json.dumps(
                {
                    "schema_version": ML_V2_SCHEMA_VERSION,
                    "target": TARGET_COLUMN,
                    "feature_order": list(MODEL_FEATURE_COLUMNS),
                    "smoothing": self.smoothing,
                    "global_target_mean": self.global_target_mean,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "category_encodings": str(category_path),
            "historical_features": str(history_path),
            "feature_schema": str(schema_path),
        }

    @classmethod
    def load(cls, directory: str | Path) -> "FeatureEncodingBundle":
        source = Path(directory)
        schema = json.loads((source / "feature_schema.json").read_text(encoding="utf-8"))
        if schema.get("schema_version") != ML_V2_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported ML V2 feature schema: {schema.get('schema_version')!r}."
            )
        if tuple(schema.get("feature_order", [])) != MODEL_FEATURE_COLUMNS:
            raise ValueError("ML V2 feature order does not match the runtime contract.")
        history = pd.read_parquet(source / "historical_features.parquet")
        return cls(
            smoothing=float(schema["smoothing"]),
            global_target_mean=float(schema["global_target_mean"]),
            category_encodings=pd.read_parquet(source / "category_encodings.parquet"),
            edge_history=history[history["history_type"] == "edge"]
            .drop(columns=["history_type"])
            .dropna(axis=1, how="all"),
            route_history=history[history["history_type"] == "route"]
            .drop(columns=["history_type"])
            .dropna(axis=1, how="all"),
        )
