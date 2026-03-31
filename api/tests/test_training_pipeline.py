from __future__ import annotations

import unittest

import pandas as pd

from training.config import (
    ArtifactConfig,
    DataConfig,
    FeatureConfig,
    ModelConfig,
    SmokeConfig,
    SplitConfig,
    TargetConfig,
    TrainingConfig,
)
from training.data import annotate_trip_start, derive_segment_dataset, split_dataset
from training.features import build_training_frame


def make_config() -> TrainingConfig:
    return TrainingConfig(
        data=DataConfig(
            dataset_path="data/raw/simulation/bus_delay_simulation.parquet",
        ),
        split=SplitConfig(
            train_fraction=0.5,
            validation_fraction=0.25,
            test_fraction=0.25,
            group_by="trip_id",
            sort_by="trip_start_scheduled_unix",
        ),
        targets=TargetConfig(),
        stop_smoke_features=FeatureConfig(
            categorical=["route_id", "stop_id"],
            numeric=[
                "stop_sequence",
                "normalized_stop_position",
                "distance_to_prev_stop_km",
                "hour_of_day",
                "day_of_week",
                "prev_delay",
                "rolling_delay_3",
            ],
            drop=["trip_id"],
        ),
        segment_features=FeatureConfig(
            categorical=["route_id", "from_stop_id", "to_stop_id"],
            numeric=[
                "stop_sequence",
                "normalized_stop_position",
                "distance_to_prev_stop_km",
                "hour_of_day",
                "day_of_week",
                "prev_segment_delay",
                "rolling_segment_delay_3",
                "scheduled_segment_minutes",
            ],
            drop=["trip_id"],
        ),
        smoke=SmokeConfig(enabled=True, sample_rows=10),
        model=ModelConfig(n_estimators=10, max_depth=3),
        artifacts=ArtifactConfig(
            model_path="artifacts/models/test_model.joblib",
            metrics_path="artifacts/metrics/test_metrics.json",
            schema_path="artifacts/models/test_schema.json",
            config_snapshot_path="artifacts/metrics/test_config.json",
            smoke_metrics_path="artifacts/metrics/test_smoke_metrics.json",
        ),
    )


def make_raw_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "trip_id": "trip_a",
                "route_id": 1,
                "stop_id": 100,
                "stop_sequence": 0,
                "normalized_stop_position": 0.0,
                "scheduled_arrival_unix": 60,
                "gps_timestamp": 60,
                "hour_of_day": 8,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 0.0,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.0,
            },
            {
                "trip_id": "trip_a",
                "route_id": 1,
                "stop_id": 101,
                "stop_sequence": 1,
                "normalized_stop_position": 0.5,
                "scheduled_arrival_unix": 120,
                "gps_timestamp": 126,
                "hour_of_day": 8,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 1.2,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.1,
            },
            {
                "trip_id": "trip_a",
                "route_id": 1,
                "stop_id": 102,
                "stop_sequence": 2,
                "normalized_stop_position": 1.0,
                "scheduled_arrival_unix": 180,
                "gps_timestamp": 198,
                "hour_of_day": 8,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 1.0,
                "prev_delay": 0.1,
                "rolling_delay_3": 0.1,
                "delay_minutes": 0.3,
            },
            {
                "trip_id": "trip_b",
                "route_id": 2,
                "stop_id": 200,
                "stop_sequence": 0,
                "normalized_stop_position": 0.0,
                "scheduled_arrival_unix": 240,
                "gps_timestamp": 240,
                "hour_of_day": 9,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 0.0,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.0,
            },
            {
                "trip_id": "trip_b",
                "route_id": 2,
                "stop_id": 201,
                "stop_sequence": 1,
                "normalized_stop_position": 1.0,
                "scheduled_arrival_unix": 300,
                "gps_timestamp": 309,
                "hour_of_day": 9,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 2.5,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.15,
            },
            {
                "trip_id": "trip_c",
                "route_id": 3,
                "stop_id": 300,
                "stop_sequence": 0,
                "normalized_stop_position": 0.0,
                "scheduled_arrival_unix": 360,
                "gps_timestamp": 360,
                "hour_of_day": 10,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 0.0,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.0,
            },
            {
                "trip_id": "trip_c",
                "route_id": 3,
                "stop_id": 301,
                "stop_sequence": 1,
                "normalized_stop_position": 1.0,
                "scheduled_arrival_unix": 420,
                "gps_timestamp": 426,
                "hour_of_day": 10,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 1.8,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.1,
            },
            {
                "trip_id": "trip_d",
                "route_id": 4,
                "stop_id": 400,
                "stop_sequence": 0,
                "normalized_stop_position": 0.0,
                "scheduled_arrival_unix": 480,
                "gps_timestamp": 480,
                "hour_of_day": 11,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 0.0,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.0,
            },
            {
                "trip_id": "trip_d",
                "route_id": 4,
                "stop_id": 401,
                "stop_sequence": 1,
                "normalized_stop_position": 1.0,
                "scheduled_arrival_unix": 540,
                "gps_timestamp": 555,
                "hour_of_day": 11,
                "day_of_week": 1,
                "distance_to_prev_stop_km": 1.4,
                "prev_delay": 0.0,
                "rolling_delay_3": 0.0,
                "delay_minutes": 0.25,
            },
        ]
    )


class TrainingPipelineTests(unittest.TestCase):
    def test_segment_derivation_computes_expected_values(self) -> None:
        config = make_config()
        raw_dataframe = make_raw_dataframe()

        segment_dataframe = derive_segment_dataset(raw_dataframe, config)

        self.assertEqual(len(segment_dataframe), 5)

        first_trip_rows = segment_dataframe[segment_dataframe["trip_id"] == "trip_a"]
        self.assertEqual(first_trip_rows.iloc[0]["from_stop_id"], 100.0)
        self.assertEqual(first_trip_rows.iloc[0]["to_stop_id"], 101)
        self.assertAlmostEqual(first_trip_rows.iloc[0]["scheduled_segment_minutes"], 1.0)
        self.assertAlmostEqual(first_trip_rows.iloc[0]["actual_segment_minutes"], 1.1)
        self.assertAlmostEqual(first_trip_rows.iloc[0]["segment_delay_minutes"], 0.1)
        self.assertAlmostEqual(first_trip_rows.iloc[0]["prev_segment_delay"], 0.0)
        self.assertAlmostEqual(first_trip_rows.iloc[0]["rolling_segment_delay_3"], 0.0)
        self.assertAlmostEqual(first_trip_rows.iloc[1]["prev_segment_delay"], 0.1)
        self.assertAlmostEqual(first_trip_rows.iloc[1]["rolling_segment_delay_3"], 0.1)

    def test_grouped_split_has_no_trip_overlap(self) -> None:
        config = make_config()
        annotated = annotate_trip_start(make_raw_dataframe(), config)

        train_frame, validation_frame, test_frame = split_dataset(annotated, config)

        train_trips = set(train_frame["trip_id"].unique())
        validation_trips = set(validation_frame["trip_id"].unique())
        test_trips = set(test_frame["trip_id"].unique())

        self.assertFalse(train_trips & validation_trips)
        self.assertFalse(validation_trips & test_trips)
        self.assertFalse(train_trips & test_trips)

    def test_build_training_frame_uses_segment_features(self) -> None:
        config = make_config()
        segment_dataframe = derive_segment_dataset(make_raw_dataframe(), config)

        features, target = build_training_frame(
            segment_dataframe,
            config.segment_features,
            config.targets.canonical_target,
        )

        self.assertListEqual(
            list(features.columns),
            config.segment_features.categorical + config.segment_features.numeric,
        )
        self.assertEqual(target.name, config.targets.canonical_target)


if __name__ == "__main__":
    unittest.main()
