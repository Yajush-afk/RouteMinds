from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from api.app.core.config import REPO_ROOT
from api.app.core.exceptions import (
    ModelArtifactMissingException,
    PredictionRequestException,
)
from api.app.ml.predictor import SegmentTravelTimePredictor
from api.training.config import load_training_config, resolve_repo_path

MIN_PREDICTED_SEGMENT_MINUTES = 0.01
DEFAULT_TRAINING_CONFIG_PATH = "api/training/config/default_config.toml"
DEFAULT_ROUTE_EDGE_SUPPORT_PATH = (
    "artifacts/models/xgboost_segment_travel_time_supported_edges.parquet"
)

logger = logging.getLogger(__name__)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _estimate_segment_uncertainty(
    *,
    predicted_actual_segment_minutes: float,
    scheduled_segment_minutes: float,
    record: dict[str, Any],
) -> float:
    predicted_delay = predicted_actual_segment_minutes - scheduled_segment_minutes
    prev_segment_delay = abs(float(record.get("prev_segment_delay", 0.0)))
    rolling_segment_delay_3 = abs(float(record.get("rolling_segment_delay_3", 0.0)))
    route_delay_minutes_live = abs(float(record.get("route_delay_minutes_live", 0.0)))
    segment_slowdown_index = max(1.0, float(record.get("segment_slowdown_index", 1.0)))
    corridor_slowdown_score_live = max(
        1.0,
        float(record.get("corridor_slowdown_score_live", 1.0)),
    )
    bunching_indicator = max(0.0, float(record.get("bunching_indicator", 0.0)))
    headway_irregularity_score_live = max(
        0.0,
        float(record.get("headway_irregularity_score_live", 0.0)),
    )
    stop_recent_arrival_gap_minutes = max(
        0.0,
        float(record.get("stop_recent_arrival_gap_minutes", 0.0)),
    )

    baseline_minutes = max(1.0, scheduled_segment_minutes)
    uncertainty_minutes = 0.6
    uncertainty_minutes += min(1.2, baseline_minutes * 0.12)
    uncertainty_minutes += min(1.5, abs(predicted_delay) * 0.18)
    uncertainty_minutes += min(1.0, prev_segment_delay * 0.08)
    uncertainty_minutes += min(1.2, rolling_segment_delay_3 * 0.1)
    uncertainty_minutes += min(1.0, (segment_slowdown_index - 1.0) * 1.2)
    uncertainty_minutes += min(1.0, (corridor_slowdown_score_live - 1.0) * 1.0)
    uncertainty_minutes += min(0.8, headway_irregularity_score_live * 0.8)
    uncertainty_minutes += min(0.5, bunching_indicator * 0.5)
    uncertainty_minutes += min(0.8, route_delay_minutes_live / 10.0)
    uncertainty_minutes += min(0.4, stop_recent_arrival_gap_minutes / 20.0)
    return _clamp(uncertainty_minutes, 0.5, 8.0)


def _estimate_segment_reliability_score(
    *,
    predicted_actual_segment_minutes: float,
    scheduled_segment_minutes: float,
    segment_uncertainty: float,
    record: dict[str, Any],
) -> float:
    baseline_minutes = max(1.0, scheduled_segment_minutes)
    uncertainty_pressure = segment_uncertainty / (baseline_minutes + 2.0)
    slowdown_pressure = max(0.0, float(record.get("segment_slowdown_index", 1.0)) - 1.0)
    corridor_pressure = max(
        0.0,
        float(record.get("corridor_slowdown_score_live", 1.0)) - 1.0,
    )
    headway_pressure = max(0.0, float(record.get("headway_irregularity_score_live", 0.0)))
    bunching_pressure = max(0.0, float(record.get("bunching_indicator", 0.0)))
    route_delay_pressure = max(0.0, float(record.get("route_delay_minutes_live", 0.0))) / 15.0
    predicted_delay_pressure = abs(
        predicted_actual_segment_minutes - scheduled_segment_minutes
    ) / (baseline_minutes + 2.0)

    instability_score = 0.0
    instability_score += min(0.45, uncertainty_pressure * 0.45)
    instability_score += min(0.15, slowdown_pressure * 0.2)
    instability_score += min(0.1, corridor_pressure * 0.15)
    instability_score += min(0.15, headway_pressure * 0.15)
    instability_score += min(0.05, bunching_pressure * 0.05)
    instability_score += min(0.05, route_delay_pressure * 0.05)
    instability_score += min(0.05, predicted_delay_pressure * 0.1)
    return _clamp(1.0 - instability_score, 0.05, 0.99)

def resolve_app_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


@lru_cache(maxsize=4)
def load_supported_route_edges(
    training_config_path: str | Path = DEFAULT_TRAINING_CONFIG_PATH,
) -> frozenset[tuple[str, str, str]]:
    support_path = resolve_app_path(DEFAULT_ROUTE_EDGE_SUPPORT_PATH)
    if support_path.exists():
        support_frame = pd.read_parquet(support_path)
        return frozenset(
            zip(
                support_frame["route_id"].astype(str),
                support_frame["from_stop_id"].astype(str),
                support_frame["to_stop_id"].astype(str),
            )
        )

    config = load_training_config(training_config_path)
    dataset_path = resolve_repo_path(config.data.dataset_path)
    columns = [
        config.data.trip_id_column,
        config.data.route_id_column,
        config.data.stop_id_column,
        config.data.stop_sequence_column,
        config.data.scheduled_time_column,
    ]

    suffix = dataset_path.suffix.lower()
    if suffix == ".csv" or config.data.file_format.lower() == "csv":
        frame = pd.read_csv(dataset_path, usecols=columns)
    elif suffix == ".parquet" or config.data.file_format.lower() == "parquet":
        frame = pd.read_parquet(dataset_path, columns=columns)
    else:
        raise ValueError(
            "Unsupported dataset format for loading model support edges. "
            "Use CSV or Parquet."
        )

    frame = frame.sort_values(
        [
            config.data.trip_id_column,
            config.data.stop_sequence_column,
            config.data.scheduled_time_column,
        ]
    ).reset_index(drop=True)
    frame["from_stop_id"] = frame.groupby(
        config.data.trip_id_column,
        sort=False,
    )[config.data.stop_id_column].shift(1)
    supported_segments = frame[frame["from_stop_id"].notna()]
    return frozenset(
        zip(
            supported_segments[config.data.route_id_column].astype(str),
            supported_segments["from_stop_id"].astype(str),
            supported_segments[config.data.stop_id_column].astype(str),
        )
    )

class PredictionService:
    def __init__(
        self,
        model_path: str | Path,
        schema_path: str | Path,
        training_config_path: str | Path = DEFAULT_TRAINING_CONFIG_PATH,
    ):
        self.model_path = resolve_app_path(model_path)
        self.schema_path = resolve_app_path(schema_path)
        self.training_config_path = str(training_config_path)
        self._support_check_warning_emitted = False
        self.predictor = SegmentTravelTimePredictor(
            model_path=self.model_path,
            schema_path=self.schema_path,
        )

    def supports_segment_record(self, segment_record: dict[str, Any]) -> bool:
        try:
            supported_route_edges = load_supported_route_edges(self.training_config_path)
        except Exception as exc:  # pragma: no cover - defensive fallback
            if not self._support_check_warning_emitted:
                logger.warning(
                    "Unable to load route-edge support set from training data; "
                    "continuing without OOD protection: %s",
                    exc,
                )
                self._support_check_warning_emitted = True
            return True

        route_edge_key = (
            str(segment_record["route_id"]),
            str(segment_record["from_stop_id"]),
            str(segment_record["to_stop_id"]),
        )
        return route_edge_key in supported_route_edges

    def predict_segments(
        self,
        segment_records: list[dict[str, Any]],
    ) -> list[dict[str, float | str | bool]]:
        if not self.schema_path.exists():
            raise ModelArtifactMissingException("schema", str(self.schema_path))
        if not self.model_path.exists():
            raise ModelArtifactMissingException("model", str(self.model_path))

        try:
            travel_time_predictions = self.predictor.predict_batch(segment_records)
        except ValueError as exc:
            raise PredictionRequestException(str(exc)) from exc

        predictions: list[dict[str, float | str | bool]] = []
        for prediction, record in zip(travel_time_predictions, segment_records, strict=True):
            scheduled_segment_minutes = float(record["scheduled_segment_minutes"])
            predicted_actual_segment_minutes = max(
                MIN_PREDICTED_SEGMENT_MINUTES,
                float(prediction),
            )
            predicted_segment_delay_minutes = float(
                predicted_actual_segment_minutes - scheduled_segment_minutes
            )
            segment_uncertainty = _estimate_segment_uncertainty(
                predicted_actual_segment_minutes=predicted_actual_segment_minutes,
                scheduled_segment_minutes=scheduled_segment_minutes,
                record=record,
            )
            segment_reliability_score = _estimate_segment_reliability_score(
                predicted_actual_segment_minutes=predicted_actual_segment_minutes,
                scheduled_segment_minutes=scheduled_segment_minutes,
                segment_uncertainty=segment_uncertainty,
                record=record,
            )
            congestion_proxy_ratio = (
                predicted_actual_segment_minutes / max(0.1, scheduled_segment_minutes)
            )
            predictions.append(
                {
                    "predicted_actual_segment_minutes": predicted_actual_segment_minutes,
                    "predicted_segment_delay_minutes": predicted_segment_delay_minutes,
                    "segment_uncertainty": segment_uncertainty,
                    "segment_reliability_score": segment_reliability_score,
                    "congestion_proxy_ratio": congestion_proxy_ratio,
                    "congestion_proxy_percent": (congestion_proxy_ratio - 1.0) * 100.0,
                    "predicted_eta_lower_minutes": max(
                        MIN_PREDICTED_SEGMENT_MINUTES,
                        predicted_actual_segment_minutes - segment_uncertainty,
                    ),
                    "predicted_eta_upper_minutes": (
                        predicted_actual_segment_minutes + segment_uncertainty
                    ),
                    "prediction_source": "ml",
                    "model_supported": True,
                }
            )

        return predictions
