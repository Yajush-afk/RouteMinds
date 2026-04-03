from __future__ import annotations
from pathlib import Path
from typing import Any
from api.app.core.config import REPO_ROOT
from api.app.core.exceptions import (
    ModelArtifactMissingException,
    PredictionRequestException,
)
from api.app.ml.predictor import SegmentTravelTimePredictor

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
            predictions.append(
                {
                    "predicted_actual_segment_minutes": float(prediction),
                    "predicted_segment_delay_minutes": float(
                        prediction - scheduled_segment_minutes
                    ),
                }
            )

        return predictions
