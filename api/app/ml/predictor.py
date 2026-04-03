from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from api.app.ml.model_loader import load_model
from api.common.features import prepare_model_frame


class SegmentTravelTimePredictor:
    def __init__(self, model_path: str | Path, schema_path: str | Path | None = None):
        self.model_path = Path(model_path)
        self.schema_path = Path(schema_path) if schema_path else None

    def _load_schema(self) -> dict | None:
        if not self.schema_path:
            return None
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema artifact not found at '{self.schema_path}'.")
        return json.loads(self.schema_path.read_text(encoding="utf-8"))

    def _prepare_dataframe(self, records: list[dict]) -> pd.DataFrame:
        dataframe = pd.DataFrame(records)
        schema = self._load_schema()
        if not schema:
            return dataframe

        dataframe = prepare_model_frame(
            dataframe,
            categorical_columns=schema["categorical_features"],
            numeric_columns=schema["numeric_features"],
            feature_time_column=schema.get("feature_time_column"),
        )
        feature_columns = schema["categorical_features"] + schema["numeric_features"]

        return dataframe[feature_columns].copy()

    def predict_batch(self, records: list[dict]) -> list[float]:
        dataframe = self._prepare_dataframe(records)
        model = load_model(self.model_path)
        predictions = model.predict(dataframe)
        return [float(value) for value in predictions]

    def predict_delay_batch(self, records: list[dict]) -> list[float]:
        predictions = self.predict_batch(records)
        delay_predictions: list[float] = []
        for prediction, record in zip(predictions, records, strict=True):
            if "scheduled_segment_minutes" not in record:
                raise ValueError(
                    "Prediction payload must include 'scheduled_segment_minutes' "
                    "to derive segment delay predictions."
                )
            delay_predictions.append(
                float(prediction - float(record["scheduled_segment_minutes"]))
            )
        return delay_predictions


DelayPredictor = SegmentTravelTimePredictor
