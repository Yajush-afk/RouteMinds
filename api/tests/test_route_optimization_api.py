from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from api.app.api.v1.routes import optimize_route
from api.app.core.auth import require_auth
from api.app.core.config import settings
from api.app.core.exceptions import RouteNotFoundException, StopNotFoundException
from api.app.main import app
from api.app.schemas.routes import RouteOptimizationRequest
from api.app.services.realtime_enrichment_service import scheduled_unix_from_service_date
from api.app.services.gtfs_graph_service import SegmentEdge, StaticTransitGraph, StopNode
from api.app.services.route_optimization_service import RouteOptimizationService


class StubPredictionService:
    def __init__(self, weights: dict[tuple[str, str], float]):
        self.weights = weights

    def predict_segments(self, segment_records: list[dict]) -> list[dict[str, float]]:
        predictions = []
        for record in segment_records:
            key = (str(record["from_stop_id"]), str(record["to_stop_id"]))
            predicted_actual = self.weights[key]
            predictions.append(
                {
                    "predicted_actual_segment_minutes": predicted_actual,
                    "predicted_segment_delay_minutes": predicted_actual
                    - float(record["scheduled_segment_minutes"]),
                }
            )
        return predictions


class StubGraphService:
    def __init__(self, graph: StaticTransitGraph):
        self.graph = graph

    def get_graph(self) -> StaticTransitGraph:
        return self.graph


class StubRealtimeWaitService:
    def __init__(
        self,
        *,
        scheduled_headway_minutes: float | None = None,
        recent_arrival_gap_minutes: float = 0.0,
        headway_irregularity_score_live: float = 0.0,
        bunching_indicator: float = 0.0,
        rolling_route_delay_minutes: float = 0.0,
    ):
        self.scheduled_headway_minutes = scheduled_headway_minutes
        self.recent_arrival_gap_minutes = recent_arrival_gap_minutes
        self.headway_irregularity_score_live = headway_irregularity_score_live
        self.bunching_indicator = bunching_indicator
        self.rolling_route_delay_minutes = rolling_route_delay_minutes

    def get_segment_live_context(self, *args, **kwargs):
        return None

    def get_stop_live_context(self, *args, **kwargs):
        return type(
            "StopContext",
            (),
            {
                "recent_arrival_gap_minutes": self.recent_arrival_gap_minutes,
                "headway_irregularity_score_live": self.headway_irregularity_score_live,
                "bunching_indicator": self.bunching_indicator,
                "last_update_timestamp": kwargs.get("reference_timestamp", 0),
            },
        )()

    def get_route_live_context(self, *args, **kwargs):
        return type(
            "RouteContext",
            (),
            {
                "rolling_route_delay_minutes": self.rolling_route_delay_minutes,
                "corridor_slowdown_score_live": 1.0,
                "bunching_indicator": self.bunching_indicator,
                "headway_irregularity_score_live": self.headway_irregularity_score_live,
                "last_update_timestamp": kwargs.get("reference_timestamp", 0),
            },
        )()

    def get_scheduled_headway_minutes(self, *args, **kwargs):
        return self.scheduled_headway_minutes


def build_test_graph() -> StaticTransitGraph:
    stops = {
        "A": StopNode("A", "Stop A", 28.70, 77.10),
        "B": StopNode("B", "Stop B", 28.71, 77.11),
        "C": StopNode("C", "Stop C", 28.72, 77.12),
        "D": StopNode("D", "Stop D", 28.73, 77.13),
    }
    edges = (
        SegmentEdge("R1", "A", "B", 1, 0.5, 1.0, 5.0),
        SegmentEdge("R1", "B", "C", 2, 1.0, 1.0, 5.0),
        SegmentEdge("R2", "A", "C", 1, 1.0, 2.0, 20.0),
    )
    return StaticTransitGraph(
        stops_by_id=stops,
        edges=edges,
        edges_from_stop={
            "A": (edges[0], edges[2]),
            "B": (edges[1],),
        },
    )


class RouteOptimizationServiceTests(unittest.TestCase):
    def test_service_chooses_lowest_total_predicted_path(self) -> None:
        graph_service = StubGraphService(build_test_graph())
        prediction_service = StubPredictionService(
            {
                ("A", "B"): 4.0,
                ("B", "C"): 4.0,
                ("A", "C"): 12.0,
            }
        )
        service = RouteOptimizationService(graph_service, prediction_service)

        result = service.optimize_route("A", "C", 1742803800)

        self.assertEqual([stop["stop_id"] for stop in result.stops], ["A", "B", "C"])
        self.assertEqual(len(result.segments), 2)
        self.assertAlmostEqual(result.total_predicted_eta_minutes, 8.0)

    def test_same_origin_and_destination_returns_zero_eta(self) -> None:
        graph_service = StubGraphService(build_test_graph())
        prediction_service = StubPredictionService({})
        service = RouteOptimizationService(graph_service, prediction_service)

        result = service.optimize_route("A", "A", 1742803800)

        self.assertEqual([stop["stop_id"] for stop in result.stops], ["A"])
        self.assertEqual(result.segments, [])
        self.assertEqual(result.total_predicted_eta_minutes, 0.0)

    def test_unknown_stop_raises_not_found(self) -> None:
        graph_service = StubGraphService(build_test_graph())
        prediction_service = StubPredictionService({})
        service = RouteOptimizationService(graph_service, prediction_service)

        with self.assertRaises(StopNotFoundException):
            service.optimize_route("UNKNOWN", "C", 1742803800)

    def test_unreachable_stop_raises_route_not_found(self) -> None:
        graph_service = StubGraphService(build_test_graph())
        prediction_service = StubPredictionService(
            {
                ("A", "B"): 4.0,
                ("B", "C"): 4.0,
                ("A", "C"): 12.0,
            }
        )
        service = RouteOptimizationService(graph_service, prediction_service)

        with self.assertRaises(RouteNotFoundException):
            service.optimize_route("A", "D", 1742803800)

    def test_service_scores_downstream_edges_with_arrival_time(self) -> None:
        class TimeAwarePredictionService:
            def __init__(self):
                self.timestamps: list[int] = []

            def predict_segments(self, segment_records: list[dict]) -> list[dict[str, float]]:
                predictions = []
                for record in segment_records:
                    timestamp = int(record["segment_start_scheduled_unix"])
                    self.timestamps.append(timestamp)
                    edge_key = (
                        str(record["from_stop_id"]),
                        str(record["to_stop_id"]),
                    )
                    if edge_key == ("A", "B"):
                        predicted_actual = 10.0
                    elif edge_key == ("A", "C"):
                        predicted_actual = 30.0
                    else:
                        predicted_actual = 5.0
                    predictions.append(
                        {
                            "predicted_actual_segment_minutes": predicted_actual,
                            "predicted_segment_delay_minutes": predicted_actual
                            - float(record["scheduled_segment_minutes"]),
                        }
                    )
                return predictions

        graph_service = StubGraphService(build_test_graph())
        prediction_service = TimeAwarePredictionService()
        service = RouteOptimizationService(graph_service, prediction_service)

        service.optimize_route("A", "C", 1742803800)

        self.assertIn(1742803800, prediction_service.timestamps)
        self.assertIn(1742804400, prediction_service.timestamps)

    def test_service_accounts_for_transfer_wait_and_buffer(self) -> None:
        query_timestamp = scheduled_unix_from_service_date("20250401", 8 * 3600)
        stops = {
            "A": StopNode("A", "Stop A", 28.70, 77.10),
            "B": StopNode("B", "Stop B", 28.71, 77.11),
            "C": StopNode("C", "Stop C", 28.72, 77.12),
        }
        transfer_edges = (
            SegmentEdge("R1", "A", "B", 1, 0.5, 1.0, 5.0, (8 * 3600,)),
            SegmentEdge("R2", "B", "C", 2, 1.0, 1.0, 5.0, (8 * 3600 + 9 * 60,)),
            SegmentEdge("R3", "A", "C", 1, 1.0, 2.0, 10.0, (8 * 3600 + 60,)),
        )
        graph = StaticTransitGraph(
            stops_by_id=stops,
            edges=transfer_edges,
            edges_from_stop={
                "A": (transfer_edges[0], transfer_edges[2]),
                "B": (transfer_edges[1],),
            },
        )
        graph_service = StubGraphService(graph)
        prediction_service = StubPredictionService(
            {
                ("A", "B"): 2.0,
                ("B", "C"): 2.0,
                ("A", "C"): 7.0,
            }
        )
        service = RouteOptimizationService(graph_service, prediction_service)

        result = service.optimize_route("A", "C", query_timestamp)

        self.assertEqual([stop["stop_id"] for stop in result.stops], ["A", "C"])
        self.assertEqual(len(result.segments), 1)
        self.assertAlmostEqual(result.segments[0]["wait_minutes_before_boarding"], 1.0)
        self.assertAlmostEqual(result.total_predicted_eta_minutes, 8.0)

    def test_service_uses_next_feasible_departure_for_segment(self) -> None:
        query_timestamp = scheduled_unix_from_service_date("20250401", 8 * 3600)
        stops = {
            "A": StopNode("A", "Stop A", 28.70, 77.10),
            "C": StopNode("C", "Stop C", 28.72, 77.12),
        }
        edge = SegmentEdge(
            "R1",
            "A",
            "C",
            1,
            1.0,
            2.0,
            5.0,
            (7 * 3600 + 55 * 60, 8 * 3600 + 10 * 60),
        )
        graph = StaticTransitGraph(
            stops_by_id=stops,
            edges=(edge,),
            edges_from_stop={"A": (edge,)},
        )
        graph_service = StubGraphService(graph)
        prediction_service = StubPredictionService({("A", "C"): 4.0})
        service = RouteOptimizationService(graph_service, prediction_service)

        result = service.optimize_route("A", "C", query_timestamp)

        self.assertEqual(
            result.segments[0]["scheduled_departure_unix"], query_timestamp + 600
        )
        self.assertAlmostEqual(result.segments[0]["wait_minutes_before_boarding"], 10.0)
        self.assertAlmostEqual(result.total_predicted_eta_minutes, 14.0)

    def test_service_live_adjusts_wait_for_frequent_route_boarding(self) -> None:
        query_timestamp = scheduled_unix_from_service_date("20250401", 8 * 3600)
        stops = {
            "A": StopNode("A", "Stop A", 28.70, 77.10),
            "C": StopNode("C", "Stop C", 28.72, 77.12),
        }
        edge = SegmentEdge(
            "R1",
            "A",
            "C",
            1,
            1.0,
            2.0,
            5.0,
            (8 * 3600 + 60,),
        )
        graph = StaticTransitGraph(
            stops_by_id=stops,
            edges=(edge,),
            edges_from_stop={"A": (edge,)},
        )
        graph_service = StubGraphService(graph)
        prediction_service = StubPredictionService({("A", "C"): 4.0})
        realtime_service = StubRealtimeWaitService(
            scheduled_headway_minutes=8.0,
            recent_arrival_gap_minutes=6.0,
            headway_irregularity_score_live=0.5,
            bunching_indicator=1.0,
            rolling_route_delay_minutes=6.0,
        )
        service = RouteOptimizationService(
            graph_service,
            prediction_service,
            realtime_enrichment_service=realtime_service,
        )

        result = service.optimize_route("A", "C", query_timestamp)

        self.assertAlmostEqual(
            result.segments[0]["scheduled_wait_minutes_before_boarding"],
            1.0,
        )
        self.assertGreater(result.segments[0]["wait_minutes_before_boarding"], 1.0)
        self.assertLess(result.segments[0]["boarding_feasibility_score"], 1.0)
        self.assertGreater(result.total_predicted_eta_minutes, 5.0)

    def test_service_preserves_scheduled_wait_without_live_context(self) -> None:
        query_timestamp = scheduled_unix_from_service_date("20250401", 8 * 3600)
        stops = {
            "A": StopNode("A", "Stop A", 28.70, 77.10),
            "C": StopNode("C", "Stop C", 28.72, 77.12),
        }
        edge = SegmentEdge(
            "R1",
            "A",
            "C",
            1,
            1.0,
            2.0,
            5.0,
            (8 * 3600 + 10 * 60,),
        )
        graph = StaticTransitGraph(
            stops_by_id=stops,
            edges=(edge,),
            edges_from_stop={"A": (edge,)},
        )
        graph_service = StubGraphService(graph)
        prediction_service = StubPredictionService({("A", "C"): 4.0})
        service = RouteOptimizationService(graph_service, prediction_service)

        result = service.optimize_route("A", "C", query_timestamp)

        self.assertAlmostEqual(
            result.segments[0]["scheduled_wait_minutes_before_boarding"],
            10.0,
        )
        self.assertAlmostEqual(result.segments[0]["wait_minutes_before_boarding"], 10.0)
        self.assertEqual(result.segments[0]["boarding_feasibility_score"], 1.0)


class StubRouteOptimizationApiService:
    def optimize_route(
        self,
        origin_stop_id: str | int,
        destination_stop_id: str | int,
        query_timestamp_unix: int,
    ):
        if str(origin_stop_id) == "UNKNOWN":
            raise StopNotFoundException(str(origin_stop_id))
        if str(destination_stop_id) == "UNREACHABLE":
            raise RouteNotFoundException(str(origin_stop_id), str(destination_stop_id))
        return type(
            "Result",
            (),
            {
                "stops": [
                    {
                        "stop_id": "A",
                        "stop_name": "Stop A",
                        "stop_lat": 28.70,
                        "stop_lon": 77.10,
                    },
                    {
                        "stop_id": "B",
                        "stop_name": "Stop B",
                        "stop_lat": 28.71,
                        "stop_lon": 77.11,
                    },
                ],
                "segments": [
                    {
                        "route_id": "R1",
                        "from_stop_id": "A",
                        "to_stop_id": "B",
                        "stop_sequence": 1,
                        "normalized_stop_position": 1.0,
                        "distance_to_prev_stop_km": 1.2,
                        "scheduled_segment_minutes": 5.0,
                        "scheduled_wait_minutes_before_boarding": 0.0,
                        "boarding_feasibility_score": 0.9,
                        "predicted_actual_segment_minutes": 4.5,
                        "predicted_segment_delay_minutes": -0.5,
                    }
                ],
                "total_predicted_eta_minutes": 4.5,
            },
        )()


class RouteOptimizationApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.original_supabase_auth_enabled = settings.SUPABASE_AUTH_ENABLED
        settings.SUPABASE_AUTH_ENABLED = True
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        settings.SUPABASE_AUTH_ENABLED = self.original_supabase_auth_enabled
        app.dependency_overrides.clear()

    async def _post_route(self, payload: dict) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post("/api/v1/routes/optimize", json=payload)

    async def test_valid_request_returns_path_and_eta(self) -> None:
        with patch(
            "api.app.api.v1.routes.get_route_optimization_service",
            return_value=StubRouteOptimizationApiService(),
        ):
            response = await optimize_route(
                RouteOptimizationRequest(
                    origin_stop_id="A",
                    destination_stop_id="B",
                    query_timestamp_unix=1742803800,
                ),
                _claims={
                    "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                    "role": "authenticated",
                    "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                },
            )

        self.assertEqual(len(response.stops), 2)
        self.assertEqual(len(response.segments), 1)
        self.assertEqual(response.total_predicted_eta_minutes, 4.5)

    async def test_unknown_stop_returns_404(self) -> None:
        with patch(
            "api.app.api.v1.routes.get_route_optimization_service",
            return_value=StubRouteOptimizationApiService(),
        ):
            with self.assertRaises(StopNotFoundException):
                await optimize_route(
                    RouteOptimizationRequest(
                        origin_stop_id="UNKNOWN",
                        destination_stop_id="B",
                        query_timestamp_unix=1742803800,
                    ),
                    _claims={
                        "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                        "role": "authenticated",
                        "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    },
                )

    async def test_no_route_returns_404(self) -> None:
        with patch(
            "api.app.api.v1.routes.get_route_optimization_service",
            return_value=StubRouteOptimizationApiService(),
        ):
            with self.assertRaises(RouteNotFoundException):
                await optimize_route(
                    RouteOptimizationRequest(
                        origin_stop_id="A",
                        destination_stop_id="UNREACHABLE",
                        query_timestamp_unix=1742803800,
                    ),
                    _claims={
                        "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
                        "role": "authenticated",
                        "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
                    },
                )

    async def test_missing_required_field_returns_422(self) -> None:
        with self.assertRaises(ValidationError):
            RouteOptimizationRequest(
                origin_stop_id="A",
                query_timestamp_unix=1742803800,
            )

    async def test_missing_bearer_token_returns_401(self) -> None:
        response = await self._post_route(
            {
                "origin_stop_id": "A",
                "destination_stop_id": "B",
                "query_timestamp_unix": 1742803800,
            }
        )

        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())

    async def test_authenticated_request_returns_200(self) -> None:
        app.dependency_overrides[require_auth] = lambda: {
            "sub": "6c0a1808-4a95-4c21-85a8-44fa17c22d11",
            "role": "authenticated",
            "session_id": "6734ed6d-5101-4c88-958f-8eb6e2e27daf",
        }

        with patch(
            "api.app.api.v1.routes.get_route_optimization_service",
            return_value=StubRouteOptimizationApiService(),
        ):
            response = await self._post_route(
                {
                    "origin_stop_id": "A",
                    "destination_stop_id": "B",
                    "query_timestamp_unix": 1742803800,
                }
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("total_predicted_eta_minutes", response.json())


if __name__ == "__main__":
    unittest.main()
