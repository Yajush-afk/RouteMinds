from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from api.app.core.exceptions import GTFSStaticDataException
from api.app.services.gtfs_graph_service import GTFSGraphService, build_static_transit_graph


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


class GTFSGraphServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.gtfs_dir = Path(self.temp_dir.name)

        write_csv(
            self.gtfs_dir / "stops.txt",
            ["stop_code", "stop_id", "stop_lat", "stop_lon", "stop_name", "zone_id"],
            [
                ["A", "STOP_A", "28.7000", "77.1000", "Narela Terminal", "1"],
                ["B", "STOP_B", "28.7100", "77.1100", "Police Station Narela", "1"],
                ["C", "STOP_C", "28.7200", "77.1200", "Narela Sector 5", "1"],
                ["D", "STOP_D", "28.7210", "77.1210", "Narela Sec 5 Depot", "1"],
            ],
        )
        write_csv(
            self.gtfs_dir / "routes.txt",
            ["agency_id", "route_id", "route_long_name", "route_short_name", "route_type"],
            [["DIMTS", "R1", "Route 1", "", "3"]],
        )
        write_csv(
            self.gtfs_dir / "trips.txt",
            ["route_id", "service_id", "trip_id", "shape_id"],
            [["R1", "WK", "TRIP_1", ""], ["R1", "WK", "TRIP_2", ""]],
        )
        write_csv(
            self.gtfs_dir / "stop_times.txt",
            ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
            [
                ["TRIP_1", "08:00:00", "08:00:00", "STOP_A", "0"],
                ["TRIP_1", "08:05:00", "08:05:00", "STOP_B", "1"],
                ["TRIP_1", "08:10:00", "08:10:00", "STOP_C", "2"],
                ["TRIP_2", "09:00:00", "09:00:00", "STOP_A", "0"],
                ["TRIP_2", "09:05:00", "09:05:00", "STOP_C", "1"],
                ["TRIP_2", "09:10:00", "09:10:00", "STOP_D", "2"],
            ],
        )

    def tearDown(self) -> None:
        build_static_transit_graph.cache_clear()
        self.temp_dir.cleanup()

    def test_builds_graph_with_expected_edge_attributes(self) -> None:
        service = GTFSGraphService(self.gtfs_dir)

        graph = service.get_graph()

        self.assertEqual(graph.stop_count, 4)
        self.assertEqual(graph.edge_count, 4)

        first_edge = graph.get_outgoing_edges("STOP_A")[0]
        self.assertEqual(first_edge.route_id, "R1")
        self.assertEqual(first_edge.from_stop_id, "STOP_A")
        self.assertEqual(first_edge.to_stop_id, "STOP_B")
        self.assertEqual(first_edge.stop_sequence, 1)
        self.assertAlmostEqual(first_edge.normalized_stop_position, 0.5)
        self.assertAlmostEqual(first_edge.scheduled_segment_minutes, 5.0)
        self.assertEqual(first_edge.scheduled_departure_seconds, (8 * 3600,))
        self.assertGreater(first_edge.distance_to_prev_stop_km, 0.0)

    def test_builds_same_graph_when_stop_times_are_unsorted(self) -> None:
        write_csv(
            self.gtfs_dir / "stop_times.txt",
            ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
            [
                ["TRIP_1", "08:10:00", "08:10:00", "STOP_C", "2"],
                ["TRIP_1", "08:00:00", "08:00:00", "STOP_A", "0"],
                ["TRIP_1", "08:05:00", "08:05:00", "STOP_B", "1"],
            ],
        )

        service = GTFSGraphService(self.gtfs_dir)
        graph = service.get_graph()

        self.assertEqual(graph.edge_count, 4)
        outgoing = graph.get_outgoing_edges("STOP_A")
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0].to_stop_id, "STOP_B")
        self.assertEqual(outgoing[0].scheduled_departure_seconds, (8 * 3600,))

    def test_graph_builder_is_cached_for_same_directory(self) -> None:
        service = GTFSGraphService(self.gtfs_dir)

        first_graph = service.get_graph()
        second_graph = service.get_graph()

        self.assertIs(first_graph, second_graph)

    def test_missing_required_gtfs_file_raises_clear_error(self) -> None:
        (self.gtfs_dir / "routes.txt").unlink()
        service = GTFSGraphService(self.gtfs_dir)

        with self.assertRaises(GTFSStaticDataException) as context:
            service.get_graph()

        self.assertIn("routes.txt", str(context.exception))

    def test_stop_search_handles_aliases_and_popularity(self) -> None:
        service = GTFSGraphService(self.gtfs_dir)

        results = service.search_stops("narela sec 5", limit=3)

        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["stop_id"], "STOP_C")
        self.assertEqual(results[1]["stop_id"], "STOP_D")

    def test_stop_search_handles_fuzzy_queries(self) -> None:
        service = GTFSGraphService(self.gtfs_dir)

        results = service.search_stops("police staton narela", limit=3)

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["stop_id"], "STOP_B")


if __name__ == "__main__":
    unittest.main()
