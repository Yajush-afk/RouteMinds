from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

try:
    from google.transit import gtfs_realtime_pb2
except ImportError:
    gtfs_realtime_pb2 = None

from api.app.api.v1.realtime import refresh_realtime, realtime_status
from api.app.core.config import settings
from api.app.core.exceptions import GTFSRealtimeException
from api.app.main import app
from api.app.services.gtfs_graph_service import SegmentEdge, StaticTransitGraph, StopNode
from api.app.services.realtime_enrichment_service import (
    GTFSRealtimeIngestionService,
    RealtimeEnrichmentService,
    VehiclePositionSnapshot,
    scheduled_unix_from_service_date,
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
        [
            ["R1", "WK", "TRIP_1", ""],
            ["R1", "WK", "TRIP_2", ""],
        ],
    )
    write_csv(
        temp_dir / "stop_times.txt",
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        [
            ["TRIP_1", "08:00:00", "08:00:00", "STOP_A", "0"],
            ["TRIP_1", "08:05:00", "08:05:00", "STOP_B", "1"],
            ["TRIP_1", "08:10:00", "08:10:00", "STOP_C", "2"],
            ["TRIP_2", "09:00:00", "09:00:00", "STOP_A", "0"],
            ["TRIP_2", "09:05:00", "09:05:00", "STOP_B", "1"],
            ["TRIP_2", "09:10:00", "09:10:00", "STOP_C", "2"],
        ],
    )


def build_protobuf_payload() -> bytes:
    if gtfs_realtime_pb2 is None:
        raise unittest.SkipTest("gtfs-realtime-bindings is not installed")

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    feed.header.timestamp = 1743494825
    entity = feed.entity.add()
    entity.id = "entity-1"
    vehicle = entity.vehicle
    vehicle.trip.trip_id = "TRIP_1"
    vehicle.trip.route_id = "R1"
    vehicle.trip.start_time = "08:00:00"
    vehicle.trip.start_date = "20250401"
    vehicle.vehicle.id = "V1"
    vehicle.position.latitude = 28.709
    vehicle.position.longitude = 77.109
    vehicle.position.speed = 5.5
    vehicle.timestamp = 1743494820
    return feed.SerializeToString()


def make_snapshot(
    *,
    vehicle_id: str,
    trip_id: str,
    route_id: str = "R1",
    start_time: str = "08:00:00",
    start_date: str = "20250401",
    latitude: float = 28.709,
    longitude: float = 77.109,
    speed_mps: float = 5.5,
    gps_timestamp: int | None = None,
    snapshot_time: int | None = None,
) -> VehiclePositionSnapshot:
    gps_timestamp = gps_timestamp or scheduled_unix_from_service_date(start_date, 8 * 3600 + 6 * 60)
    snapshot_time = snapshot_time or gps_timestamp + 5
    return VehiclePositionSnapshot(
        vehicle_id=vehicle_id,
        trip_id=trip_id,
        route_id=route_id,
        start_time=start_time,
        start_date=start_date,
        latitude=latitude,
        longitude=longitude,
        speed_mps=speed_mps,
        gps_timestamp=gps_timestamp,
        snapshot_time=snapshot_time,
    )


class FakeIngestionService:
    def __init__(self, snapshots: list[VehiclePositionSnapshot]):
        self.snapshots = snapshots
        self.vehicle_positions_url = "https://example.com/vehicles"
        self.api_key = "secret"
        self.last_provider_format = "json"
        self.last_raw_record_count = len(snapshots)
        self.last_malformed_record_count = 0

    def fetch_vehicle_positions(self) -> list[VehiclePositionSnapshot]:
        return self.snapshots

    def _resolve_auth_mode(self) -> str:
        return "headers"


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
    def __init__(self, edge: SegmentEdge | None = None):
        edge = edge or SegmentEdge("R1", "STOP_A", "STOP_B", 1, 0.5, 1.0, 4.0)
        from_stop = edge.from_stop_id
        self.graph = StaticTransitGraph(
            stops_by_id={
                "STOP_A": StopNode("STOP_A", "Stop A", 28.70, 77.10),
                "STOP_B": StopNode("STOP_B", "Stop B", 28.71, 77.11),
                "STOP_C": StopNode("STOP_C", "Stop C", 28.72, 77.12),
            },
            edges=(edge,),
            edges_from_stop={from_stop: (edge,)},
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

    def test_fetcher_normalizes_valid_json_payload(self) -> None:
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
                    "gps_timestamp": scheduled_unix_from_service_date("20250401", 8 * 3600 + 7 * 60),
                    "snapshot_time": scheduled_unix_from_service_date("20250401", 8 * 3600 + 7 * 60 + 5),
                }
            ]
        }

        snapshots = service._normalize_json_response(payload)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].vehicle_id, "V1")
        self.assertEqual(service.last_provider_format, None)
        self.assertEqual(service.last_raw_record_count, 1)

    def test_fetcher_supports_protobuf_payload_with_query_key_auth(self) -> None:
        service = GTFSRealtimeIngestionService(
            vehicle_positions_url="https://otd.delhi.gov.in/api/realtime/VehiclePositions.pb",
            api_key="secret",
        )
        protobuf_payload = build_protobuf_payload()

        def fake_get(url, timeout, params, headers):
            self.assertEqual(params, {"key": "secret"})
            self.assertEqual(headers, {})
            return httpx.Response(
                200,
                content=protobuf_payload,
                headers={"content-type": "application/x-protobuf"},
                request=httpx.Request("GET", url, params=params),
            )

        with patch("api.app.services.realtime_enrichment_service.httpx.get", side_effect=fake_get):
            snapshots = service.fetch_vehicle_positions()

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].trip_id, "TRIP_1")
        self.assertEqual(service.last_provider_format, "protobuf")
        self.assertEqual(service.last_raw_record_count, 1)
        self.assertEqual(service.last_malformed_record_count, 0)

    def test_fetcher_raises_clear_error_without_protobuf_bindings(self) -> None:
        service = GTFSRealtimeIngestionService(
            vehicle_positions_url="https://otd.delhi.gov.in/api/realtime/VehiclePositions.pb",
            api_key="secret",
        )

        with patch("api.app.services.realtime_enrichment_service.gtfs_realtime_pb2", None):
            with self.assertRaises(GTFSRealtimeException) as context:
                service._normalize_protobuf_response(b"protobuf-payload")

        self.assertIn("gtfs-realtime-bindings", str(context.exception))

    def test_missing_api_key_raises_clear_error(self) -> None:
        service = GTFSRealtimeIngestionService(
            vehicle_positions_url="https://example.com/vehicles",
            api_key="",
        )

        with self.assertRaises(GTFSRealtimeException):
            service.fetch_vehicle_positions()

    def test_fetcher_rejects_unstructured_payload(self) -> None:
        service = GTFSRealtimeIngestionService(
            vehicle_positions_url="https://example.com/vehicles",
            api_key="secret",
        )

        with self.assertRaises(GTFSRealtimeException):
            service._normalize_json_response({"unexpected": "shape"})

    def test_enrichment_builds_segment_live_context(self) -> None:
        trip_1_stop_b_arrival = scheduled_unix_from_service_date("20250401", 8 * 3600 + 5 * 60)
        trip_1_ab_midpoint = scheduled_unix_from_service_date("20250401", 8 * 3600 + 2 * 60 + 30)
        trip_1_stop_c_arrival = scheduled_unix_from_service_date("20250401", 8 * 3600 + 10 * 60)
        snapshots = [
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                latitude=28.705,
                longitude=77.105,
                gps_timestamp=trip_1_ab_midpoint + 90,
                snapshot_time=trip_1_ab_midpoint + 95,
            ),
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                latitude=28.715,
                longitude=77.115,
                gps_timestamp=trip_1_stop_c_arrival + 180,
                snapshot_time=trip_1_stop_c_arrival + 185,
            ),
        ]
        service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )

        result = service.refresh_vehicle_positions()
        context = service.get_segment_live_context(
            "R1",
            "STOP_B",
            "STOP_C",
            reference_timestamp=trip_1_stop_c_arrival + 200,
        )

        self.assertEqual(result["fetched_snapshots"], 2)
        self.assertEqual(result["enriched_segments"], 2)
        self.assertEqual(result["unmatched_snapshots"], 0)
        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(context.route_id, "R1")
        self.assertEqual(context.from_stop_id, "STOP_B")
        self.assertEqual(context.to_stop_id, "STOP_C")
        self.assertEqual(context.prev_segment_delay, 0.0)
        self.assertNotEqual(context.rolling_segment_delay_3, 0.0)

    def test_latest_vehicle_on_same_segment_wins(self) -> None:
        trip_1_stop_b_arrival = scheduled_unix_from_service_date("20250401", 8 * 3600 + 5 * 60)
        snapshots = [
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                latitude=28.705,
                longitude=77.105,
                gps_timestamp=scheduled_unix_from_service_date("20250401", 8 * 3600 + 3 * 60),
                snapshot_time=scheduled_unix_from_service_date("20250401", 8 * 3600 + 3 * 60 + 5),
            ),
            make_snapshot(
                vehicle_id="V2",
                trip_id="TRIP_1",
                latitude=28.706,
                longitude=77.106,
                gps_timestamp=scheduled_unix_from_service_date("20250401", 8 * 3600 + 4 * 60),
                snapshot_time=scheduled_unix_from_service_date("20250401", 8 * 3600 + 4 * 60 + 5),
            ),
        ]
        service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )

        service.refresh_vehicle_positions()
        context = service.get_segment_live_context(
            "R1",
            "STOP_A",
            "STOP_B",
            reference_timestamp=trip_1_stop_b_arrival,
        )

        assert context is not None
        self.assertEqual(context.vehicle_id, "V2")
        self.assertEqual(
            context.last_update_timestamp,
            scheduled_unix_from_service_date("20250401", 8 * 3600 + 4 * 60 + 5),
        )

    def test_trip_change_for_same_vehicle_does_not_bleed_delay_history(self) -> None:
        trip_1_stop_b_arrival = scheduled_unix_from_service_date("20250401", 8 * 3600 + 5 * 60)
        trip_2_stop_b_arrival = scheduled_unix_from_service_date("20250401", 9 * 3600 + 5 * 60)
        snapshots = [
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                latitude=28.705,
                longitude=77.105,
                gps_timestamp=scheduled_unix_from_service_date("20250401", 8 * 3600 + 3 * 60),
                snapshot_time=scheduled_unix_from_service_date("20250401", 8 * 3600 + 3 * 60 + 5),
            ),
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_2",
                start_time="09:00:00",
                latitude=28.705,
                longitude=77.105,
                gps_timestamp=scheduled_unix_from_service_date("20250401", 9 * 3600 + 3 * 60),
                snapshot_time=scheduled_unix_from_service_date("20250401", 9 * 3600 + 3 * 60 + 5),
            ),
        ]
        service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )

        service.refresh_vehicle_positions()
        context = service.get_segment_live_context(
            "R1",
            "STOP_A",
            "STOP_B",
            reference_timestamp=trip_2_stop_b_arrival,
        )

        assert context is not None
        self.assertEqual(context.trip_id, "TRIP_2")
        self.assertEqual(context.prev_segment_delay, 0.0)
        self.assertNotEqual(context.rolling_segment_delay_3, 0.0)

    def test_refresh_tracks_unmatched_trip_and_vehicle_counts(self) -> None:
        snapshots = [
            make_snapshot(vehicle_id="V1", trip_id="", gps_timestamp=scheduled_unix_from_service_date("20250401", 8 * 3600 + 60)),
            make_snapshot(vehicle_id="V2", trip_id="UNKNOWN_TRIP"),
            make_snapshot(vehicle_id="V3", trip_id="TRIP_1"),
        ]
        service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )

        result = service.refresh_vehicle_positions()

        self.assertEqual(result["fetched_snapshots"], 3)
        self.assertEqual(result["enriched_segments"], 1)
        self.assertEqual(result["unmatched_snapshots"], 2)
        self.assertEqual(result["unmatched_trips"], 1)
        self.assertEqual(result["unmatched_vehicles"], 2)

    def test_routing_uses_live_delay_context_when_available(self) -> None:
        trip_1_stop_c_arrival = scheduled_unix_from_service_date("20250401", 8 * 3600 + 10 * 60)
        snapshots = [
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                latitude=28.719,
                longitude=77.119,
                gps_timestamp=trip_1_stop_c_arrival + 180,
                snapshot_time=trip_1_stop_c_arrival + 185,
            ),
        ]
        realtime_service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )
        realtime_service.refresh_vehicle_positions()

        prediction_service = StaticPredictionService()
        route_service = RouteOptimizationService(
            graph_service=StaticGraphService(
                SegmentEdge("R1", "STOP_B", "STOP_C", 2, 1.0, 1.0, 5.0)
            ),
            prediction_service=prediction_service,
            realtime_enrichment_service=realtime_service,
        )

        with patch(
            "api.app.services.realtime_enrichment_service.time.time",
            return_value=trip_1_stop_c_arrival + 200,
        ):
            route_service.optimize_route("STOP_B", "STOP_C", trip_1_stop_c_arrival + 200)

        self.assertGreaterEqual(prediction_service.last_records[0]["prev_segment_delay"], 0.0)
        self.assertGreater(prediction_service.last_records[0]["rolling_segment_delay_3"], 0.0)

    def test_routing_uses_static_route_id_for_live_context_lookup(self) -> None:
        trip_1_stop_c_arrival = scheduled_unix_from_service_date("20250401", 8 * 3600 + 10 * 60)
        snapshots = [
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                route_id="PROVIDER_ROUTE_ID",
                latitude=28.719,
                longitude=77.119,
                gps_timestamp=trip_1_stop_c_arrival + 180,
                snapshot_time=trip_1_stop_c_arrival + 185,
            ),
        ]
        realtime_service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
        )

        realtime_service.refresh_vehicle_positions()
        context = realtime_service.get_segment_live_context(
            "R1",
            "STOP_B",
            "STOP_C",
            reference_timestamp=trip_1_stop_c_arrival + 200,
        )

        assert context is not None
        self.assertEqual(context.route_id, "R1")

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

        route_service.optimize_route("STOP_A", "STOP_B", scheduled_unix_from_service_date("20250401", 8 * 3600))

        self.assertEqual(prediction_service.last_records[0]["prev_segment_delay"], 0.0)
        self.assertEqual(prediction_service.last_records[0]["rolling_segment_delay_3"], 0.0)

    def test_stale_live_context_falls_back_to_zero(self) -> None:
        trip_1_stop_b_arrival = scheduled_unix_from_service_date("20250401", 8 * 3600 + 5 * 60)
        snapshots = [
            make_snapshot(
                vehicle_id="V1",
                trip_id="TRIP_1",
                gps_timestamp=trip_1_stop_b_arrival + 120,
                snapshot_time=trip_1_stop_b_arrival + 125,
            ),
        ]
        realtime_service = RealtimeEnrichmentService(
            gtfs_static_dir=self.gtfs_dir,
            ingestion_service=FakeIngestionService(snapshots),
            cache_max_age_seconds=60,
        )
        realtime_service.refresh_vehicle_positions()

        prediction_service = StaticPredictionService()
        route_service = RouteOptimizationService(
            graph_service=StaticGraphService(),
            prediction_service=prediction_service,
            realtime_enrichment_service=realtime_service,
        )

        route_service.optimize_route("STOP_A", "STOP_B", trip_1_stop_b_arrival + 600)

        self.assertEqual(prediction_service.last_records[0]["prev_segment_delay"], 0.0)
        self.assertEqual(prediction_service.last_records[0]["rolling_segment_delay_3"], 0.0)
        self.assertFalse(realtime_service.get_status()["cache_is_fresh"])

    def test_snapshot_persistence_writes_json_file(self) -> None:
        snapshot_path = self.gtfs_dir / "snapshots.json"
        service = GTFSRealtimeIngestionService(
            vehicle_positions_url="https://example.com/vehicles",
            api_key="secret",
            snapshot_path=snapshot_path,
        )
        snapshots = [
            make_snapshot(vehicle_id="V1", trip_id="TRIP_1"),
        ]

        service._persist_snapshots(snapshots)

        self.assertTrue(snapshot_path.exists())
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(payload[0]["vehicle_id"], "V1")


class StubRealtimeApiService:
    def refresh_vehicle_positions(self) -> dict[str, int | bool | str | None]:
        return {
            "fetched_snapshots": 3,
            "enriched_segments": 2,
            "latest_snapshot_time": 1743495000,
            "unmatched_snapshots": 1,
            "unmatched_trips": 1,
            "unmatched_vehicles": 1,
            "malformed_records": 0,
            "provider_format": "protobuf",
            "auth_mode": "query",
            "last_refresh_successful": True,
            "last_refresh_error": None,
        }

    def get_status(self) -> dict[str, int | bool | str | None]:
        return {
            "configured": True,
            "last_refresh_time": 1743495010,
            "last_successful_refresh_time": 1743495010,
            "latest_snapshot_time": 1743495000,
            "fetched_snapshots": 3,
            "enriched_segments": 2,
            "unmatched_snapshots": 1,
            "unmatched_trips": 1,
            "unmatched_vehicles": 1,
            "malformed_records": 0,
            "cached_segments": 2,
            "cached_vehicles": 1,
            "cache_max_age_seconds": 300,
            "cache_is_fresh": True,
            "provider_format": "protobuf",
            "auth_mode": "query",
            "last_refresh_successful": True,
            "last_refresh_error": None,
        }


class RealtimeApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_supabase_auth_enabled = settings.SUPABASE_AUTH_ENABLED
        settings.SUPABASE_AUTH_ENABLED = True
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = self.original_supabase_auth_enabled
        app.dependency_overrides.clear()

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
            response = await refresh_realtime(
                _claims={
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    "app_metadata": {"permissions": ["realtime:manage"]},
                }
            )

        self.assertEqual(response.fetched_snapshots, 3)
        self.assertEqual(response.enriched_segments, 2)
        self.assertEqual(response.provider_format, "protobuf")

    async def test_status_endpoint_returns_cache_state(self) -> None:
        with patch(
            "api.app.api.v1.realtime.get_realtime_enrichment_service",
            return_value=StubRealtimeApiService(),
        ):
            response = await realtime_status(
                _claims={
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    "app_metadata": {"permissions": ["realtime:manage"]},
                }
            )

        self.assertTrue(response.configured)
        self.assertEqual(response.cached_segments, 2)
        self.assertTrue(response.cache_is_fresh)
        self.assertEqual(response.auth_mode, "query")

    async def test_realtime_endpoints_require_bearer_token(self) -> None:
        refresh_response = await self._request("POST", "/api/v1/realtime/refresh")
        status_response = await self._request("GET", "/api/v1/realtime/status")

        self.assertEqual(refresh_response.status_code, 401)
        self.assertEqual(status_response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
