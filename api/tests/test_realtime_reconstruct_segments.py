from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from api.app.services.realtime_enrichment_service import scheduled_unix_from_service_date
from api.training.reconstruct_realtime_segments import reconstruct_realtime_segments


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def build_gtfs_fixture(temp_dir: Path) -> None:
    write_csv(
        temp_dir / "stops.txt",
        ["stop_code", "stop_id", "stop_lat", "stop_lon", "stop_name", "zone_id"],
        [
            ["A", "STOP_A", "28.7000", "77.1000", "Stop A", "1"],
            ["B", "STOP_B", "28.7100", "77.1100", "Stop B", "1"],
            ["C", "STOP_C", "28.7200", "77.1200", "Stop C", "1"],
            ["D", "STOP_D", "28.7300", "77.1300", "Stop D", "1"],
        ],
    )
    write_csv(
        temp_dir / "routes.txt",
        ["agency_id", "route_id", "route_long_name", "route_short_name", "route_type"],
        [["DIMTS", "R1", "Route 1", "", "3"]],
    )
    write_csv(
        temp_dir / "trips.txt",
        ["route_id", "service_id", "trip_id", "shape_id"],
        [["R1", "WK", "TRIP_1", ""]],
    )
    write_csv(
        temp_dir / "stop_times.txt",
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        [
            ["TRIP_1", "08:00:00", "08:00:00", "STOP_A", "0"],
            ["TRIP_1", "08:05:00", "08:05:00", "STOP_B", "1"],
            ["TRIP_1", "08:10:00", "08:10:00", "STOP_C", "2"],
            ["TRIP_1", "08:15:00", "08:15:00", "STOP_D", "3"],
        ],
    )


def build_canonical_snapshot_fixture(output_dir: Path) -> None:
    partition_dir = output_dir / "service_date=20250401"
    partition_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        [
            {
                "service_date": "20250401",
                "snapshot_date": "20250401",
                "vehicle_id": "V1",
                "trip_id": "TRIP_1",
                "route_id": "R1",
                "start_time": "08:00:00",
                "start_date": "20250401",
                "latitude": 28.705,
                "longitude": 77.105,
                "speed_mps": 0.0,
                "gps_timestamp": scheduled_unix_from_service_date("20250401", 8 * 3600 + 2 * 60),
                "snapshot_time": pd.Timestamp("2025-04-01T08:02:05Z"),
                "snapshot_timestamp_unix": scheduled_unix_from_service_date("20250401", 8 * 3600 + 2 * 60 + 5),
            },
            {
                "service_date": "20250401",
                "snapshot_date": "20250401",
                "vehicle_id": "V1",
                "trip_id": "TRIP_1",
                "route_id": "R1",
                "start_time": "08:00:00",
                "start_date": "20250401",
                "latitude": 28.715,
                "longitude": 77.115,
                "speed_mps": 0.0,
                "gps_timestamp": scheduled_unix_from_service_date("20250401", 8 * 3600 + 7 * 60),
                "snapshot_time": pd.Timestamp("2025-04-01T08:07:05Z"),
                "snapshot_timestamp_unix": scheduled_unix_from_service_date("20250401", 8 * 3600 + 7 * 60 + 5),
            },
            {
                "service_date": "20250401",
                "snapshot_date": "20250401",
                "vehicle_id": "V1",
                "trip_id": "TRIP_1",
                "route_id": "R1",
                "start_time": "08:00:00",
                "start_date": "20250401",
                "latitude": 28.725,
                "longitude": 77.125,
                "speed_mps": 0.0,
                "gps_timestamp": scheduled_unix_from_service_date("20250401", 8 * 3600 + 12 * 60),
                "snapshot_time": pd.Timestamp("2025-04-01T08:12:05Z"),
                "snapshot_timestamp_unix": scheduled_unix_from_service_date("20250401", 8 * 3600 + 12 * 60 + 5),
            },
        ]
    )
    frame.to_parquet(partition_dir / "part-00001.parquet", index=False)


class RealtimeSegmentReconstructionTests(unittest.TestCase):
    def test_reconstruction_writes_segment_rows_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            gtfs_dir = temp_path / "gtfs"
            canonical_dir = temp_path / "canonical"
            output_dir = temp_path / "segments"
            report_path = temp_path / "report.json"
            gtfs_dir.mkdir(parents=True, exist_ok=True)
            build_gtfs_fixture(gtfs_dir)
            build_canonical_snapshot_fixture(canonical_dir)

            report = reconstruct_realtime_segments(
                input_dir=canonical_dir,
                output_dir=output_dir,
                report_path=report_path,
                gtfs_static_dir=gtfs_dir,
                max_service_dates=0,
            )

            self.assertEqual(report["service_dates_processed"], 1)
            self.assertEqual(report["traces_processed"], 1)
            self.assertEqual(report["exact_trip_matches"], 1)
            self.assertGreaterEqual(report["reconstructed_segments"], 3)
            self.assertTrue(report_path.exists())

            segment_file = output_dir / "service_date=20250401.parquet"
            self.assertTrue(segment_file.exists())
            segment_frame = pd.read_parquet(segment_file)
            self.assertIn("actual_segment_minutes", segment_frame.columns)
            self.assertIn("reconstruction_confidence_score", segment_frame.columns)
            self.assertIn("used_estimated_start_boundary", segment_frame.columns)
            self.assertIn("supervised_training_eligible", segment_frame.columns)
            self.assertGreaterEqual(len(segment_frame), 3)

            middle_segment = segment_frame[
                (segment_frame["from_stop_id"] == "STOP_B")
                & (segment_frame["to_stop_id"] == "STOP_C")
            ].iloc[0]
            self.assertFalse(bool(middle_segment["used_estimated_start_boundary"]))
            self.assertFalse(bool(middle_segment["used_estimated_end_boundary"]))
            self.assertAlmostEqual(float(middle_segment["actual_segment_minutes"]), 5.0, places=2)
            self.assertGreaterEqual(
                float(middle_segment["reconstruction_confidence_score"]),
                0.8,
            )
            self.assertTrue(bool(middle_segment["supervised_training_eligible"]))
            self.assertEqual(middle_segment["match_strategy"], "exact_trip_id")
            self.assertEqual(middle_segment["static_trip_id"], "TRIP_1")
            self.assertEqual(middle_segment["realtime_trip_id"], "TRIP_1")

            alignment_file = output_dir / "trace_alignment" / "service_date=20250401.parquet"
            self.assertTrue(alignment_file.exists())
            alignment_frame = pd.read_parquet(alignment_file)
            self.assertEqual(alignment_frame.iloc[0]["match_strategy"], "exact_trip_id")

            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report_payload["reconstructed_segments"], report["reconstructed_segments"])


if __name__ == "__main__":
    unittest.main()
