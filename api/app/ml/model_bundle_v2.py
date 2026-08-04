from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from api.common.features_v2 import FeatureEncodingBundle
from api.training.schemas import ML_V2_SCHEMA_VERSION


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True, slots=True)
class QuantilePrediction:
    p10_minutes: float
    p50_minutes: float
    p90_minutes: float
    feature_quality_score: float
    live_context_used: bool


class MLV2ModelBundle:
    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"ML V2 manifest not found at '{self.manifest_path}'.")
        self.model_dir = self.manifest_path.parent
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if self.manifest.get("schema_version") != ML_V2_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported ML V2 model schema: {self.manifest.get('schema_version')!r}."
            )
        self.model_version = str(self.manifest["model_version"])
        self.calibration_scale = float(self.manifest.get("calibration_scale", 1.0))
        self._validate_checksums()
        self.feature_bundle = FeatureEncodingBundle.load(self.model_dir)
        self.models = {
            name: self._load_model(self.model_dir / f"{name}_model.json")
            for name in ("p10", "p50", "p90")
        }

    def _validate_checksums(self) -> None:
        expected = self.manifest.get("artifact_checksums", {})
        for filename, checksum in expected.items():
            path = self.model_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"ML V2 artifact not found at '{path}'.")
            if _sha256(path) != checksum:
                raise ValueError(f"ML V2 artifact checksum mismatch: {filename}.")

    @staticmethod
    def _load_model(path: Path) -> XGBRegressor:
        model = XGBRegressor()
        model.load_model(path)
        return model

    @staticmethod
    def _minutes(scheduled: np.ndarray, log_ratio) -> np.ndarray:
        return np.clip(
            scheduled * np.exp(np.clip(np.asarray(log_ratio, dtype=float), -4.0, 4.0)),
            0.01,
            120.0,
        )

    @staticmethod
    def _feature_quality(record: dict[str, Any], historical_count: float) -> float:
        support_quality = min(1.0, math.log1p(max(0.0, historical_count)) / math.log(51.0))
        live_available = float(record.get("live_context_available", 0.0)) > 0.0
        if live_available:
            age = max(0.0, float(record.get("live_context_age_seconds", 0.0)))
            observation_count = max(
                0.0, float(record.get("live_context_observation_count", 0.0))
            )
            freshness = max(0.0, 1.0 - age / 300.0)
            live_quality = freshness * min(1.0, observation_count / 5.0)
        else:
            live_quality = 0.5
        reconstruction_quality = _clamp(
            float(record.get("reconstruction_confidence_score", 1.0)), 0.0, 1.0
        )
        return _clamp(
            support_quality * 0.55 + live_quality * 0.25 + reconstruction_quality * 0.20,
            0.05,
            1.0,
        )

    @staticmethod
    def _apply_live_correction(
        record: dict[str, Any],
        scheduled: float,
        p10: float,
        p50: float,
        p90: float,
    ) -> tuple[float, float, float, bool]:
        live_available = float(record.get("live_context_available", 0.0)) > 0.0
        if not live_available:
            return p10, p50, p90, False
        age = max(0.0, float(record.get("live_context_age_seconds", 0.0)))
        count = max(0.0, float(record.get("live_context_observation_count", 0.0)))
        confidence = max(0.0, 1.0 - age / 300.0) * min(1.0, count / 5.0)
        if confidence <= 0.0:
            return p10, p50, p90, False
        live_ratio = max(
            1.0,
            float(record.get("segment_slowdown_index", 1.0)),
            float(record.get("corridor_slowdown_score_live", 1.0)),
        )
        live_minutes = scheduled * live_ratio
        blend_weight = min(0.20, confidence * 0.20)
        corrected_p50 = p50 * (1.0 - blend_weight) + live_minutes * blend_weight
        shift = corrected_p50 - p50
        return (
            _clamp(p10 + shift, 0.01, corrected_p50),
            _clamp(corrected_p50, 0.01, 120.0),
            _clamp(p90 + shift, corrected_p50, 120.0),
            True,
        )

    def predict_batch(self, records: list[dict[str, Any]]) -> list[QuantilePrediction]:
        if not records:
            return []
        frame = pd.DataFrame(records)
        features = self.feature_bundle.transform(frame)
        scheduled = pd.to_numeric(frame["scheduled_segment_minutes"], errors="raise").to_numpy(
            dtype=float
        )
        if not np.isfinite(scheduled).all() or (scheduled <= 0.0).any():
            raise ValueError("ML V2 requires finite positive scheduled segment minutes.")
        raw = {name: model.predict(features) for name, model in self.models.items()}
        minutes = np.sort(
            np.vstack(
                [self._minutes(scheduled, raw[name]) for name in ("p10", "p50", "p90")]
            ),
            axis=0,
        )
        if not np.isfinite(minutes).all():
            raise ValueError("ML V2 produced a non-finite quantile prediction.")
        p10, p50, p90 = minutes
        p10 = np.clip(p50 - (p50 - p10) * self.calibration_scale, 0.01, 120.0)
        p90 = np.clip(p50 + (p90 - p50) * self.calibration_scale, 0.01, 120.0)

        predictions: list[QuantilePrediction] = []
        historical_counts = features["historical_sample_count"].to_numpy(dtype=float)
        for index, record in enumerate(records):
            lower, median, upper, live_used = self._apply_live_correction(
                record,
                scheduled[index],
                float(p10[index]),
                float(p50[index]),
                float(p90[index]),
            )
            predictions.append(
                QuantilePrediction(
                    p10_minutes=lower,
                    p50_minutes=median,
                    p90_minutes=upper,
                    feature_quality_score=self._feature_quality(
                        record, historical_counts[index]
                    ),
                    live_context_used=live_used,
                )
            )
        return predictions
