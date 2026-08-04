from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from api.app.ml.model_bundle_v2 import MLV2ModelBundle
from api.app.services.gtfs_graph_service import StopNode, TripStopEvent
from api.common.features_v2 import FeatureEncodingBundle, MODEL_FEATURE_COLUMNS
from api.training.data_quality import validate_segment_frame
from api.training.evaluation_v2 import trip_metrics
from api.training.generate_segment_simulation_v2 import (
    SimulationConfig,
    SlowdownConfig,
    _simulate_trip,
)
from api.training.reconstruct_realtime_segments import (
    _derive_trace_speed,
    _split_trace_windows,
)
from api.training.schemas import ML_V2_SCHEMA_VERSION
from api.training.train_xgboost_v2 import _load_audit_review, chronological_split


def make_v2_frame(rows: int = 30) -> pd.DataFrame:
    records = []
    for index in range(rows):
        scheduled = 2.0 + (index % 3) * 0.25
        actual = scheduled * (1.0 + (index % 5) * 0.04)
        records.append(
            {
                "service_date": f"202504{1 + index // 10:02d}",
                "source": "simulation",
                "trip_id": f"trip-{index // 3}",
                "route_id": f"route-{index % 2}",
                "from_stop_id": f"stop-{index % 4}",
                "to_stop_id": f"stop-{(index + 1) % 4}",
                "stop_sequence": index % 8 + 1,
                "normalized_stop_position": (index % 8 + 1) / 8.0,
                "scheduled_segment_minutes": scheduled,
                "actual_segment_minutes": actual,
                "slowdown_ratio": actual / scheduled,
                "log_slowdown_ratio": np.log(actual / scheduled),
                "distance_to_prev_stop_km": 0.8,
                "segment_start_scheduled_unix": 1743500000 + index * 300,
                "reconstruction_confidence_score": 1.0,
                "sample_weight": 0.25,
            }
        )
    return pd.DataFrame(records)


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DataQualityTests(unittest.TestCase):
    def test_invalid_physical_targets_are_reported_and_removed(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "trip_id": "valid",
                    "scheduled_segment_minutes": 2.0,
                    "actual_segment_minutes": 2.5,
                    "distance_to_prev_stop_km": 1.0,
                    "actual_segment_start_unix": 100,
                    "actual_segment_end_unix": 250,
                },
                {
                    "trip_id": "negative",
                    "scheduled_segment_minutes": 2.0,
                    "actual_segment_minutes": -1.0,
                    "distance_to_prev_stop_km": 1.0,
                    "actual_segment_start_unix": 100,
                    "actual_segment_end_unix": 40,
                },
                {
                    "trip_id": "speed",
                    "scheduled_segment_minutes": 1.0,
                    "actual_segment_minutes": 0.1,
                    "distance_to_prev_stop_km": 2.0,
                    "actual_segment_start_unix": 100,
                    "actual_segment_end_unix": 106,
                },
            ]
        )
        valid, report = validate_segment_frame(frame, source="simulation")
        self.assertEqual(len(valid), 1)
        self.assertEqual(report.rejected_rows, 2)
        self.assertEqual(report.rejection_counts["nonpositive_actual_minutes"], 1)
        self.assertEqual(report.rejection_counts["speed_above_limit"], 1)

    def test_realtime_supervised_eligibility_is_a_hard_gate(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "trip_id": "trip",
                    "scheduled_segment_minutes": 2.0,
                    "actual_segment_minutes": 2.5,
                    "distance_to_prev_stop_km": 1.0,
                    "reconstruction_confidence_score": 0.9,
                    "supervised_training_eligible": False,
                }
            ]
        )

        valid, report = validate_segment_frame(frame, source="realtime")

        self.assertTrue(valid.empty)
        self.assertEqual(report.rejection_counts["not_supervised_training_eligible"], 1)


class SimulationV2Tests(unittest.TestCase):
    def test_simulation_is_deterministic_and_monotonic(self) -> None:
        simulation = SimulationConfig(42, "20250401", 28, 100, "unused", 50, 1.0)
        slowdown = SlowdownConfig(
            7, 10, 16, 20, 1.2, 1.25, 1.0, 0.1, 0.08, 0.1, 0.12, 0.85, 0.25, 4.5, 0.1
        )
        events = (
            TripStopEvent("A", 1, 8 * 3600, 8 * 3600),
            TripStopEvent("B", 2, 8 * 3600 + 300, 8 * 3600 + 330),
            TripStopEvent("C", 3, 8 * 3600 + 660, 8 * 3600 + 660),
        )
        stops = {
            "A": StopNode("A", "A", 28.60, 77.20),
            "B": StopNode("B", "B", 28.61, 77.21),
            "C": StopNode("C", "C", 28.62, 77.22),
        }
        first = _simulate_trip(
            trip_id="T",
            route_id="R",
            events=events,
            stops=stops,
            service_date="20250401",
            instance=0,
            row_budget=10,
            rng=np.random.default_rng(42),
            simulation_config=simulation,
            slowdown_config=slowdown,
        )
        second = _simulate_trip(
            trip_id="T",
            route_id="R",
            events=events,
            stops=stops,
            service_date="20250401",
            instance=0,
            row_budget=10,
            rng=np.random.default_rng(42),
            simulation_config=simulation,
            slowdown_config=slowdown,
        )
        self.assertEqual(first, second)
        self.assertTrue(all(row["actual_segment_minutes"] > 0 for row in first))
        self.assertGreaterEqual(
            first[1]["actual_segment_start_unix"], first[0]["actual_segment_end_unix"]
        )


class FeatureV2Tests(unittest.TestCase):
    def test_chronological_split_uses_disjoint_dates(self) -> None:
        split = chronological_split(make_v2_frame())
        self.assertFalse(set(split.train_dates) & set(split.validation_dates))
        self.assertFalse(set(split.validation_dates) & set(split.test_dates))

    def test_oof_features_and_saved_bundle_share_feature_order(self) -> None:
        frame = make_v2_frame()
        bundle = FeatureEncodingBundle()
        training = bundle.fit_transform_oof(frame, folds=3)
        serving = bundle.transform(frame.head(2))
        self.assertTupleEqual(tuple(training.columns), MODEL_FEATURE_COLUMNS)
        self.assertTupleEqual(tuple(serving.columns), MODEL_FEATURE_COLUMNS)
        self.assertTrue(np.isfinite(training.to_numpy()).all())

        with tempfile.TemporaryDirectory() as directory:
            bundle.save(directory)
            loaded = FeatureEncodingBundle.load(directory)
            pd.testing.assert_frame_equal(serving, loaded.transform(frame.head(2)))

    def test_chronological_oof_encoding_does_not_use_current_target(self) -> None:
        frame = make_v2_frame().head(5).copy()
        frame["route_id"] = [f"unseen-{index}" for index in range(len(frame))]
        frame["from_stop_id"] = [f"from-{index}" for index in range(len(frame))]
        frame["to_stop_id"] = [f"to-{index}" for index in range(len(frame))]
        frame["log_slowdown_ratio"] = np.arange(len(frame), dtype=float)
        frame["slowdown_ratio"] = np.exp(frame["log_slowdown_ratio"])

        encoded = FeatureEncodingBundle().fit_transform_oof(frame, folds=5)

        self.assertTrue(
            (
                encoded["route_target_encoding"].iloc[1:].to_numpy()
                < frame["log_slowdown_ratio"].iloc[1:].to_numpy()
            ).all()
        )

    def test_complete_trip_metrics_keep_service_dates_isolated(self) -> None:
        frame = pd.DataFrame(
            {
                "source": ["simulation", "simulation"],
                "service_date": ["20250101", "20250102"],
                "trip_id": ["repeated-trip", "repeated-trip"],
                "actual_segment_minutes": [5.0, 5.0],
            }
        )

        metrics = trip_metrics(frame, [0.0, 10.0])

        self.assertEqual(metrics["trip_count"], 2)
        self.assertEqual(metrics["mae"], 5.0)

    def test_realtime_audit_review_controls_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            review_path = Path(directory) / "review.json"
            review_path.write_text(
                json.dumps(
                    {
                        "reviewed_trace_count": 200,
                        "route_direction_accuracy": 0.91,
                        "monotonic_progression_rate": 0.96,
                    }
                ),
                encoding="utf-8",
            )

            review, blockers = _load_audit_review(review_path)

        self.assertIsNotNone(review)
        self.assertEqual(blockers, [])


class NativeBundleTests(unittest.TestCase):
    def test_native_quantile_bundle_round_trip(self) -> None:
        frame = make_v2_frame()
        bundle = FeatureEncodingBundle().fit(frame)
        features = bundle.transform(frame)
        target = frame["log_slowdown_ratio"]
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            bundle.save(model_dir)
            for name, alpha in (("p10", 0.1), ("p50", 0.5), ("p90", 0.9)):
                model = XGBRegressor(
                    objective="reg:quantileerror",
                    quantile_alpha=alpha,
                    tree_method="hist",
                    device="cpu",
                    n_estimators=5,
                    max_depth=2,
                    n_jobs=1,
                )
                model.fit(features, target, verbose=False)
                model.save_model(model_dir / f"{name}_model.json")
            artifacts = [
                model_dir / "p10_model.json",
                model_dir / "p50_model.json",
                model_dir / "p90_model.json",
                model_dir / "feature_schema.json",
                model_dir / "category_encodings.parquet",
                model_dir / "historical_features.parquet",
            ]
            manifest = {
                "model_version": "test-v2",
                "schema_version": ML_V2_SCHEMA_VERSION,
                "calibration_scale": 1.0,
                "artifact_checksums": {path.name: _checksum(path) for path in artifacts},
            }
            manifest_path = model_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            predictor = MLV2ModelBundle(manifest_path)
            prediction = predictor.predict_batch(frame.head(1).to_dict("records"))[0]
            self.assertGreater(prediction.p10_minutes, 0.0)
            self.assertLessEqual(prediction.p10_minutes, prediction.p50_minutes)
            self.assertLessEqual(prediction.p50_minutes, prediction.p90_minutes)

            with (model_dir / "p50_model.json").open("a", encoding="utf-8") as handle:
                handle.write("corrupt")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                MLV2ModelBundle(manifest_path)


class RealtimeTraceV2Tests(unittest.TestCase):
    def test_trace_windows_split_after_thirty_minutes_and_derive_speed(self) -> None:
        frame = pd.DataFrame(
            {
                "gps_timestamp": [100, 160, 2200],
                "snapshot_timestamp_unix": [100, 160, 2200],
                "latitude": [28.60, 28.601, 28.61],
                "longitude": [77.20, 77.201, 77.21],
            }
        )
        windows = _split_trace_windows(frame)
        self.assertEqual([len(window) for window in windows], [2, 1])
        speed = _derive_trace_speed(windows[0])
        self.assertEqual(speed.iloc[0], 0.0)
        self.assertGreater(speed.iloc[1], 0.0)


if __name__ == "__main__":
    unittest.main()
