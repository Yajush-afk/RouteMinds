from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from api.training.canonicalize_realtime import (
    canonicalize_realtime_csv,
    canonicalize_snapshot_chunk,
)


def make_raw_rows() -> list[dict[str, object]]:
    return [
        {
            "vehicle_id": "V1",
            "trip_id": "TRIP_1",
            "route_id": "100",
            "start_time": "08:00:00",
            "start_date": "20260323",
            "latitude": 28.61,
            "longitude": 77.21,
            "speed_mps": 4.2,
            "gps_timestamp": 1774252800,
            "snapshot_time": "2026-03-23T08:00:01Z",
        },
        {
            "vehicle_id": "V1",
            "trip_id": "TRIP_1",
            "route_id": "100",
            "start_time": "08:00:00",
            "start_date": "20260323",
            "latitude": 28.61,
            "longitude": 77.21,
            "speed_mps": 4.2,
            "gps_timestamp": 1774252800,
            "snapshot_time": "2026-03-23T08:00:01Z",
        },
        {
            "vehicle_id": "V2",
            "trip_id": "TRIP_2",
            "route_id": "101",
            "start_time": "08:05:00",
            "start_date": "20260323",
            "latitude": 28.62,
            "longitude": 77.22,
            "speed_mps": 0.0,
            "gps_timestamp": 1774253100,
            "snapshot_time": "2026-03-23T08:05:02Z",
        },
        {
            "vehicle_id": "",
            "trip_id": "TRIP_3",
            "route_id": "102",
            "start_time": "08:10:00",
            "start_date": "20260323",
            "latitude": 28.63,
            "longitude": 77.23,
            "speed_mps": 1.0,
            "gps_timestamp": 1774253400,
            "snapshot_time": "2026-03-23T08:10:05Z",
        },
        {
            "vehicle_id": "V4",
            "trip_id": "TRIP_4",
            "route_id": "103",
            "start_time": "08:15:00",
            "start_date": "20260323",
            "latitude": 120.0,
            "longitude": 77.24,
            "speed_mps": 1.0,
            "gps_timestamp": 1774253700,
            "snapshot_time": "2026-03-23T08:15:05Z",
        },
    ]


class RealtimeCanonicalizeTests(unittest.TestCase):
    def test_canonicalize_snapshot_chunk_drops_invalid_and_duplicates(self) -> None:
        frame = pd.DataFrame(make_raw_rows())

        canonical_frame, stats = canonicalize_snapshot_chunk(frame)

        self.assertEqual(stats.raw_rows, 5)
        self.assertEqual(stats.invalid_rows, 2)
        self.assertEqual(stats.duplicate_rows, 1)
        self.assertEqual(stats.canonical_rows, 2)
        self.assertEqual(
            list(canonical_frame.columns),
            [
                "service_date",
                "snapshot_date",
                "vehicle_id",
                "trip_id",
                "route_id",
                "start_time",
                "start_date",
                "latitude",
                "longitude",
                "speed_mps",
                "gps_timestamp",
                "snapshot_time",
                "snapshot_timestamp_unix",
            ],
        )
        self.assertEqual(canonical_frame.iloc[0]["service_date"], "20260323")
        self.assertEqual(canonical_frame.iloc[0]["route_id"], "100")

    def test_canonicalize_realtime_csv_writes_partitioned_parquet_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "realtime.csv"
            output_dir = temp_path / "canonical"
            report_path = temp_path / "report.json"
            pd.DataFrame(make_raw_rows()).to_csv(input_path, index=False)

            report = canonicalize_realtime_csv(
                input_path=input_path,
                output_dir=output_dir,
                report_path=report_path,
                chunk_rows=2,
                overwrite_output=False,
            )

            self.assertEqual(report.raw_rows, 5)
            self.assertEqual(report.canonical_rows, 2)
            self.assertEqual(report.invalid_rows_dropped, 2)
            self.assertEqual(report.duplicate_rows_dropped, 1)
            self.assertEqual(report.observed_route_count, 2)
            self.assertEqual(report.observed_trip_count, 2)
            self.assertEqual(report.observed_vehicle_count, 2)
            self.assertEqual(report.non_zero_speed_rows, 1)
            self.assertTrue(report_path.exists())

            parquet_files = sorted(output_dir.glob("service_date=*/*.parquet"))
            self.assertGreaterEqual(len(parquet_files), 1)
            partition_frame = pd.concat(
                [pd.read_parquet(parquet_file) for parquet_file in parquet_files],
                ignore_index=True,
            )
            self.assertIn("snapshot_timestamp_unix", partition_frame.columns)
            self.assertEqual(len(partition_frame), 2)


if __name__ == "__main__":
    unittest.main()
