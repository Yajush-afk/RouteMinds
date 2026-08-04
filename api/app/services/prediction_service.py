from __future__ import annotations

import logging
import re
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
from api.app.ml.model_bundle_v2 import MLV2ModelBundle, QuantilePrediction
from api.training.config import load_training_config, resolve_repo_path

MIN_PREDICTED_SEGMENT_MINUTES = 0.01
DEFAULT_TRAINING_CONFIG_PATH = "api/training/config/default_config.toml"
DEFAULT_ROUTE_EDGE_SUPPORT_PATH = (
    "artifacts/models/xgboost_segment_travel_time_supported_edges.parquet"
)

logger = logging.getLogger(__name__)
_TRAILING_DECIMAL_ZERO_PATTERN = re.compile(r"^-?\d+\.0+$")


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalize_edge_identifier(value: Any) -> str:
    normalized = str(value).strip()
    if _TRAILING_DECIMAL_ZERO_PATTERN.match(normalized):
        return normalized.split(".", maxsplit=1)[0]
    return normalized


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


def _estimate_coarse_segment_minutes(record: dict[str, Any]) -> float:
    scheduled_segment_minutes = max(
        MIN_PREDICTED_SEGMENT_MINUTES,
        float(record.get("scheduled_segment_minutes", MIN_PREDICTED_SEGMENT_MINUTES)),
    )
    segment_slowdown_index = max(1.0, float(record.get("segment_slowdown_index", 1.0)))
    corridor_slowdown_score_live = max(
        1.0,
        float(record.get("corridor_slowdown_score_live", 1.0)),
    )
    route_delay_minutes_live = max(0.0, float(record.get("route_delay_minutes_live", 0.0)))
    headway_irregularity_score_live = max(
        0.0,
        float(record.get("headway_irregularity_score_live", 0.0)),
    )
    bunching_indicator = max(0.0, float(record.get("bunching_indicator", 0.0)))

    slowdown_multiplier = max(
        1.0,
        segment_slowdown_index,
        1.0 + max(0.0, corridor_slowdown_score_live - 1.0) * 0.85,
    )
    return max(
        MIN_PREDICTED_SEGMENT_MINUTES,
        (scheduled_segment_minutes * slowdown_multiplier)
        + min(4.0, route_delay_minutes_live / 6.0)
        + min(1.5, headway_irregularity_score_live * 0.9)
        + min(1.0, bunching_indicator * 0.75),
    )


def _guard_prediction_minutes(
    *,
    prediction_minutes: float,
    record: dict[str, Any],
    model_supported: bool,
) -> float:
    scheduled_segment_minutes = max(
        MIN_PREDICTED_SEGMENT_MINUTES,
        float(record.get("scheduled_segment_minutes", MIN_PREDICTED_SEGMENT_MINUTES)),
    )
    coarse_segment_minutes = _estimate_coarse_segment_minutes(record)
    bounded_prediction = max(MIN_PREDICTED_SEGMENT_MINUTES, float(prediction_minutes))
    raw_prediction = bounded_prediction

    route_delay_minutes_live = max(0.0, float(record.get("route_delay_minutes_live", 0.0)))
    segment_slowdown_pressure = max(
        0.0,
        float(record.get("segment_slowdown_index", 1.0)) - 1.0,
    )
    corridor_slowdown_pressure = max(
        0.0,
        float(record.get("corridor_slowdown_score_live", 1.0)) - 1.0,
    )
    headway_irregularity_score_live = max(
        0.0,
        float(record.get("headway_irregularity_score_live", 0.0)),
    )
    bunching_indicator = max(0.0, float(record.get("bunching_indicator", 0.0)))

    upper_multiplier = 3.0
    upper_multiplier += min(1.0, segment_slowdown_pressure)
    upper_multiplier += min(0.8, corridor_slowdown_pressure * 0.8)
    upper_multiplier += min(0.8, headway_irregularity_score_live * 0.8)
    upper_multiplier += min(0.5, bunching_indicator * 0.6)
    upper_multiplier += min(0.6, route_delay_minutes_live / 20.0)
    upper_bound_minutes = min(
        90.0,
        max(
            scheduled_segment_minutes + 20.0,
            scheduled_segment_minutes * upper_multiplier,
        ),
    )
    lower_bound_minutes = max(
        MIN_PREDICTED_SEGMENT_MINUTES,
        scheduled_segment_minutes * 0.4,
    )
    bounded_prediction = _clamp(
        bounded_prediction,
        lower_bound_minutes,
        upper_bound_minutes,
    )
    prediction_was_clipped = abs(bounded_prediction - raw_prediction) > 1e-6

    if model_supported and not prediction_was_clipped:
        return bounded_prediction

    instability_pressure = 0.0
    instability_pressure += min(0.35, segment_slowdown_pressure * 0.35)
    instability_pressure += min(0.25, corridor_slowdown_pressure * 0.25)
    instability_pressure += min(0.2, headway_irregularity_score_live * 0.2)
    instability_pressure += min(0.1, bunching_indicator * 0.1)
    instability_pressure += min(0.1, route_delay_minutes_live / 25.0)
    instability_pressure = _clamp(instability_pressure, 0.0, 1.0)

    if model_supported:
        ml_weight = _clamp(0.8 - (instability_pressure * 0.25), 0.5, 0.85)
    else:
        ml_weight = _clamp(0.35 - (instability_pressure * 0.15), 0.15, 0.4)

    guarded_prediction = (
        (bounded_prediction * ml_weight)
        + (coarse_segment_minutes * (1.0 - ml_weight))
    )
    return _clamp(guarded_prediction, lower_bound_minutes, upper_bound_minutes)


def _build_prediction_payload(
    *,
    record: dict[str, Any],
    predicted_actual_segment_minutes: float,
    prediction_source: str,
    model_supported: bool,
) -> dict[str, float | str | bool]:
    scheduled_segment_minutes = float(record["scheduled_segment_minutes"])
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
    return {
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
        "prediction_source": prediction_source,
        "model_supported": model_supported,
        "model_version": "legacy-v1",
        "live_context_used": False,
        "feature_quality_score": 0.5 if model_supported else 0.2,
        "prediction_interval_method": "fallback",
    }


def _build_v2_prediction_payload(
    *,
    record: dict[str, Any],
    prediction: QuantilePrediction,
    model_version: str,
) -> dict[str, float | str | bool]:
    scheduled_segment_minutes = max(
        MIN_PREDICTED_SEGMENT_MINUTES,
        float(record["scheduled_segment_minutes"]),
    )
    predicted_minutes = prediction.p50_minutes
    uncertainty = max(
        0.0,
        (prediction.p90_minutes - prediction.p10_minutes) / 2.0,
    )
    relative_interval_width = (
        prediction.p90_minutes - prediction.p10_minutes
    ) / max(1.0, predicted_minutes)
    reliability = _clamp(
        prediction.feature_quality_score / (1.0 + relative_interval_width),
        0.05,
        0.99,
    )
    congestion_ratio = predicted_minutes / max(0.1, scheduled_segment_minutes)
    return {
        "predicted_actual_segment_minutes": predicted_minutes,
        "predicted_segment_delay_minutes": predicted_minutes - scheduled_segment_minutes,
        "segment_uncertainty": uncertainty,
        "segment_reliability_score": reliability,
        "congestion_proxy_ratio": congestion_ratio,
        "congestion_proxy_percent": (congestion_ratio - 1.0) * 100.0,
        "predicted_eta_lower_minutes": prediction.p10_minutes,
        "predicted_eta_upper_minutes": prediction.p90_minutes,
        "prediction_source": "ml",
        "model_supported": True,
        "model_version": model_version,
        "live_context_used": prediction.live_context_used,
        "feature_quality_score": prediction.feature_quality_score,
        "prediction_interval_method": "xgboost_quantile",
    }


def _build_schedule_fallback_payload(
    record: dict[str, Any],
) -> dict[str, float | str | bool]:
    scheduled_minutes = max(
        MIN_PREDICTED_SEGMENT_MINUTES,
        float(record["scheduled_segment_minutes"]),
    )
    payload = _build_prediction_payload(
        record=record,
        predicted_actual_segment_minutes=scheduled_minutes,
        prediction_source="scheduled_fallback",
        model_supported=False,
    )
    payload["model_version"] = "schedule-fallback"
    payload["feature_quality_score"] = 0.0
    return payload

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
                support_frame["route_id"].map(_normalize_edge_identifier),
                support_frame["from_stop_id"].map(_normalize_edge_identifier),
                support_frame["to_stop_id"].map(_normalize_edge_identifier),
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
        (
            _normalize_edge_identifier(route_id),
            _normalize_edge_identifier(from_stop_id),
            _normalize_edge_identifier(to_stop_id),
        )
        for route_id, from_stop_id, to_stop_id in zip(
            supported_segments[config.data.route_id_column],
            supported_segments["from_stop_id"],
            supported_segments[config.data.stop_id_column],
            strict=True,
        )
    )

class PredictionService:
    def __init__(
        self,
        model_path: str | Path,
        schema_path: str | Path,
        training_config_path: str | Path = DEFAULT_TRAINING_CONFIG_PATH,
        v2_manifest_path: str | Path | None = None,
    ):
        self.model_path = resolve_app_path(model_path)
        self.schema_path = resolve_app_path(schema_path)
        self.training_config_path = str(training_config_path)
        self._support_check_warning_emitted = False
        self.predictor = SegmentTravelTimePredictor(
            model_path=self.model_path,
            schema_path=self.schema_path,
        )
        self._v2_configured = bool(v2_manifest_path)
        self.v2_bundle: MLV2ModelBundle | None = None
        if v2_manifest_path:
            resolved_manifest_path = resolve_app_path(v2_manifest_path)
            try:
                candidate_bundle = MLV2ModelBundle(resolved_manifest_path)
                if not candidate_bundle.manifest.get("promotion_eligible", False):
                    blockers = candidate_bundle.manifest.get("promotion_blockers", [])
                    raise ValueError(
                        "ML V2 bundle has not passed promotion gates: "
                        + "; ".join(str(blocker) for blocker in blockers)
                    )
                self.v2_bundle = candidate_bundle
            except Exception as exc:
                logger.warning(
                    "Unable to load ML V2 model bundle; using schedule fallback: %s",
                    exc,
                )

    def supports_segment_record(self, segment_record: dict[str, Any]) -> bool:
        if self.v2_bundle is not None:
            # V2 has global-mean category fallbacks and reports feature quality.
            return True
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
            _normalize_edge_identifier(segment_record["route_id"]),
            _normalize_edge_identifier(segment_record["from_stop_id"]),
            _normalize_edge_identifier(segment_record["to_stop_id"]),
        )
        return route_edge_key in supported_route_edges

    def predict_segments(
        self,
        segment_records: list[dict[str, Any]],
    ) -> list[dict[str, float | str | bool]]:
        if self.v2_bundle is not None:
            try:
                v2_predictions = self.v2_bundle.predict_batch(segment_records)
                return [
                    _build_v2_prediction_payload(
                        record=record,
                        prediction=prediction,
                        model_version=self.v2_bundle.model_version,
                    )
                    for record, prediction in zip(
                        segment_records, v2_predictions, strict=True
                    )
                ]
            except Exception as exc:
                logger.warning(
                    "ML V2 prediction failed; using schedule fallback for this batch: %s",
                    exc,
                )

        if self._v2_configured:
            return [_build_schedule_fallback_payload(record) for record in segment_records]

        if not self.schema_path.exists():
            raise ModelArtifactMissingException("schema", str(self.schema_path))
        if not self.model_path.exists():
            raise ModelArtifactMissingException("model", str(self.model_path))

        try:
            travel_time_predictions = self.predictor.predict_batch(segment_records)
        except ValueError as exc:
            raise PredictionRequestException(str(exc)) from exc

        return [
            _build_prediction_payload(
                record=record,
                predicted_actual_segment_minutes=_guard_prediction_minutes(
                    prediction_minutes=float(prediction),
                    record=record,
                    model_supported=True,
                ),
                prediction_source="ml",
                model_supported=True,
            )
            for prediction, record in zip(
                travel_time_predictions,
                segment_records,
                strict=True,
            )
        ]

    def predict_segments_for_unsupported_edges(
        self,
        segment_records: list[dict[str, Any]],
    ) -> list[dict[str, float | str | bool]]:
        if not segment_records:
            return []

        if self._v2_configured:
            return [_build_schedule_fallback_payload(record) for record in segment_records]

        try:
            travel_time_predictions = self.predictor.predict_batch(segment_records)
        except Exception:
            travel_time_predictions = [
                _estimate_coarse_segment_minutes(record)
                for record in segment_records
            ]

        return [
            _build_prediction_payload(
                record=record,
                predicted_actual_segment_minutes=_guard_prediction_minutes(
                    prediction_minutes=float(prediction),
                    record=record,
                    model_supported=False,
                ),
                prediction_source="scheduled_fallback",
                model_supported=False,
            )
            for prediction, record in zip(
                travel_time_predictions,
                segment_records,
                strict=True,
            )
        ]
