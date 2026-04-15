from __future__ import annotations

from pathlib import Path
from typing import Any

from api.app.core.config import REPO_ROOT
from api.app.core.exceptions import (
    ModelArtifactMissingException,
    PredictionRequestException,
)
from api.app.ml.predictor import SegmentTravelTimePredictor

MIN_PREDICTED_SEGMENT_MINUTES = 0.01


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

class PredictionService:
    def __init__(self, model_path: str | Path, schema_path: str | Path):
        self.model_path = resolve_app_path(model_path)
        self.schema_path = resolve_app_path(schema_path)
        self.predictor = SegmentTravelTimePredictor(
            model_path=self.model_path,
            schema_path=self.schema_path,
        )

    def predict_segments(self, segment_records: list[dict[str, Any]]) -> list[dict[str, float]]:
        if not self.schema_path.exists():
            raise ModelArtifactMissingException("schema", str(self.schema_path))
        if not self.model_path.exists():
            raise ModelArtifactMissingException("model", str(self.model_path))

        try:
            travel_time_predictions = self.predictor.predict_batch(segment_records)
        except ValueError as exc:
            raise PredictionRequestException(str(exc)) from exc

        predictions: list[dict[str, float]] = []
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
                }
            )

        return predictions
