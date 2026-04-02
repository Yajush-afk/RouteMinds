from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from api.app.core.config import settings
from api.app.core.exceptions import GTFSRealtimeException
from api.app.main import app
from api.app.services.gtfs_graph_service import SegmentEdge, StaticTransitGraph, StopNode
from api.app.services.realtime_enrichment_service import (
    GTFSRealtimeIngestionService,
    RealtimeEnrichmentService,
    VehiclePositionSnapshot,
)
from api.app.services.route_optimization_service import RouteOptimizationService


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def build_realtime_gtfs_fixture(temp_dir: Path) -> None:
    write_csv(
        temp_dir / "stops.txt",
        ["stop_code", "stop_id", "stop_lat", "stop_lon", "stop_name", "zone_id"],
        [
            ["A", "STOP_A", "28.7000", "77.1000", "Stop A", "1"],
            ["B", "STOP_B", "28.7100", "77.1100", "Stop B", "1"],
            ["C", "STOP_C", "28.7200", "77.1200", "Stop C", "1"],
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
        ],
    )


class FakeIngestionService:
    def __init__(self, snapshots: list[VehiclePositionSnapshot]):
        self.snapshots = snapshots
        self.vehicle_positions_url = "https://example.com/vehicles"
        self.api_key = "secret"

    def fetch_vehicle_positions(self) -> list[VehiclePositionSnapshot]:
        return self.snapshots


class StaticPredictionService:
    def __init__(self):
        self.last_records: list[dict] = []

    def predict_segments(self, segment_records: list[dict]) -> list[dict[str, float]]:
        self.last_records = segment_records
        return [
            {
                "predicted_actual_segment_minutes": 5.0,
                "predicted_segment_delay_minutes": 1.0,
            }
            for _ in segment_records
        ]


class StaticGraphService:
    def __init__(self):
        edge = SegmentEdge("R1", "STOP_A", "STOP_B", 1, 0.5, 1.0, 4.0)
        self.graph = StaticTransitGraph(
            stops_by_id={
                "STOP_A": StopNode("STOP_A", "Stop A", 28.70, 77.10),
                "STOP_B": StopNode("STOP_B", "Stop B", 28.71, 77.11),
            },
            edges=(edge,),
            edges_from_stop={"STOP_A": (edge,)},
        )

    def get_graph(self) -> StaticTransitGraph:
        return self.graph


class RealtimeEnrichmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.gtfs_dir = Path(self.temp_dir.name)
        build_realtime_gtfs_fixture(self.gtfs_dir)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_fetcher_normalizes_valid_payload(self) -> None:
        service = GTFSRealtimeIngestionService(
            vehicle_positions_url="https://example.com/vehicles",
            api_key="secret",
        )
        payload = {
            "data": [
                {
                    "vehicle_id": "V1",
                    "trip_id": "TRIP_1",
                    "route_id": "R1",
                    "start_time": "08:00:00",
                    "start_date": "20250401",
                    "latitude": 28.709,
                    "longitude": 77.109,
                    "speed_mps": 5.5,
                    "gps_timestamp": 1743494820,
                    "snapshot_time": 1743494825,
                }
            ]
        }

        snapshots = service._normalize_response(payload)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].vehicle_id, "V1")
        self.assertEqual(snapshots[0].trip_id, "TRIP_1")
        self.assertEqual(snapshots[0].route_id, "R1")

    def test_missing_api_key_raises_clear_error(self) -> None:
        service = GTFSRealtimeIngestionService(
            vehicle_positions_url="https://example.com/vehicles",
            api_key="",
        )

        with self.assertRaises(GTFSRealtimeException):
            service.fetch_vehicle_positions()

    def test_enrichment_builds_segment_live_context(self) -> None:
        snapshots = [
            VehiclePositionSnapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                route_id="R1",
                start_time="08:00:00",
                start_date="20250401",
                latitude=28.709,
                longitude=77.109,
                speed_mps=5.5,
                gps_timestamp=1743494820,
                snapshot_time=1743494825,
            ),
            VehiclePositionSnapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                route_id="R1",
                start_time="08:00:00",
                start_date="20250401",
                latitude=28.719,
                longitude=77.119,
                speed_mps=5.5,
                gps_timestamp=1743495180,
                snapshot_time=1743495185,
            ),
        ]
        service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )

        result = service.refresh_vehicle_positions()
        context = service.get_segment_live_context("R1", "STOP_B", "STOP_C")

        self.assertEqual(result["fetched_snapshots"], 2)
        self.assertEqual(result["enriched_segments"], 2)
        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context.route_id, "R1")
        self.assertEqual(context.from_stop_id, "STOP_B")
        self.assertEqual(context.to_stop_id, "STOP_C")
        self.assertGreaterEqual(context.rolling_segment_delay_3, context.prev_segment_delay)

    def test_routing_uses_live_delay_context_when_available(self) -> None:
        snapshots = [
            VehiclePositionSnapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                route_id="R1",
                start_time="08:00:00",
                start_date="20250401",
                latitude=28.709,
                longitude=77.109,
                speed_mps=5.5,
                gps_timestamp=1743494820,
                snapshot_time=1743494825,
            )
        ]
        realtime_service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )
        realtime_service.refresh_vehicle_positions()

        prediction_service = StaticPredictionService()
        route_service = RouteOptimizationService(
            graph_service=StaticGraphService(),
            prediction_service=prediction_service,
            realtime_enrichment_service=realtime_service,
        )

        route_service.optimize_route("STOP_A", "STOP_B", 1743494700)

        self.assertEqual(prediction_service.last_records[0]["prev_segment_delay"], 0.0)
        self.assertGreaterEqual(
            prediction_service.last_records[0]["rolling_segment_delay_3"],
            0.0,
        )

    def test_routing_falls_back_to_zero_without_live_context(self) -> None:
        realtime_service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService([]),
        )
        prediction_service = StaticPredictionService()
        route_service = RouteOptimizationService(
            graph_service=StaticGraphService(),
            prediction_service=prediction_service,
            realtime_enrichment_service=realtime_service,
        )

        route_service.optimize_route("STOP_A", "STOP_B", 1743494700)

        self.assertEqual(prediction_service.last_records[0]["prev_segment_delay"], 0.0)
        self.assertEqual(prediction_service.last_records[0]["rolling_segment_delay_3"], 0.0)


class StubRealtimeApiService:
    def refresh_vehicle_positions(self) -> dict[str, int | None]:
        return {
            "fetched_snapshots": 3,
            "enriched_segments": 2,
            "latest_snapshot_time": 1743495000,
        }

    def get_status(self) -> dict[str, int | bool | None]:
        return {
            "configured": True,
            "last_refresh_time": 1743495010,
            "latest_snapshot_time": 1743495000,
            "cached_segments": 2,
            "cached_vehicles": 1,
        }


class RealtimeApiTests(unittest.IsolatedAsyncioTestCase):
    async def _request(self, method: str, path: str) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path)

    async def test_refresh_endpoint_returns_operational_state(self) -> None:
        with patch(
            "api.app.api.v1.realtime.get_realtime_enrichment_service",
            return_value=StubRealtimeApiService(),
        ):
            response = await self._request("POST", "/api/v1/realtime/refresh")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["fetched_snapshots"], 3)
        self.assertEqual(payload["enriched_segments"], 2)

    async def test_status_endpoint_returns_cache_state(self) -> None:
        with patch(
            "api.app.api.v1.realtime.get_realtime_enrichment_service",
            return_value=StubRealtimeApiService(),
        ):
            response = await self._request("GET", "/api/v1/realtime/status")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["configured"])
        self.assertEqual(payload["cached_segments"], 2)


if __name__ == "__main__":
    unittest.main()
