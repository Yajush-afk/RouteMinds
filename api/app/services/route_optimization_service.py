from __future__ import annotations

import heapq
from dataclasses import dataclass

from api.app.core.exceptions import RouteNotFoundException, StopNotFoundException
from api.app.services.gtfs_graph_service import (
    GTFSGraphService,
    SegmentEdge,
    StaticTransitGraph,
)
from api.app.services.prediction_service import PredictionService
from api.app.services.realtime_enrichment_service import RealtimeEnrichmentService

MIN_EDGE_WEIGHT_MINUTES = 0.01


@dataclass(frozen=True, slots=True)
class RouteOptimizationResult:
    stops: list[dict[str, str | float]]
    segments: list[dict[str, str | int | float]]
    total_predicted_eta_minutes: float


class RouteOptimizationService:
    def __init__(
        self,
        graph_service: GTFSGraphService,
        prediction_service: PredictionService,
        realtime_enrichment_service: RealtimeEnrichmentService | None = None,
    ):
        self.graph_service = graph_service
        self.prediction_service = prediction_service
        self.realtime_enrichment_service = realtime_enrichment_service

    def optimize_route(
        self,
        origin_stop_id: str | int,
        destination_stop_id: str | int,
        query_timestamp_unix: int,
    ) -> RouteOptimizationResult:
        graph = self.graph_service.get_graph()
        origin_stop_key = str(origin_stop_id)
        destination_stop_key = str(destination_stop_id)

        if origin_stop_key not in graph.stops_by_id:
            raise StopNotFoundException(origin_stop_key)
        if destination_stop_key not in graph.stops_by_id:
            raise StopNotFoundException(destination_stop_key)

        if origin_stop_key == destination_stop_key:
            stop = graph.stops_by_id[origin_stop_key]
            return RouteOptimizationResult(
                stops=[
                    {
                        "stop_id": stop.stop_id,
                        "stop_name": stop.stop_name,
                        "stop_lat": stop.stop_lat,
                        "stop_lon": stop.stop_lon,
                    }
                ],
                segments=[],
                total_predicted_eta_minutes=0.0,
            )

        previous_edge_by_stop, edge_prediction_cache, distances = self._run_dijkstra(
            graph,
            origin_stop_key,
            destination_stop_key,
            query_timestamp_unix,
        )

        if destination_stop_key not in previous_edge_by_stop:
            raise RouteNotFoundException(origin_stop_key, destination_stop_key)

        route_edges = self._reconstruct_edges(
            previous_edge_by_stop,
            destination_stop_key,
        )
        stops = self._build_stop_path(graph, origin_stop_key, route_edges)
        segments = self._build_segment_predictions(route_edges, edge_prediction_cache)

        return RouteOptimizationResult(
            stops=stops,
            segments=segments,
            total_predicted_eta_minutes=float(distances[destination_stop_key]),
        )

    def _run_dijkstra(
        self,
        graph: StaticTransitGraph,
        origin_stop_id: str,
        destination_stop_id: str,
        query_timestamp_unix: int,
    ) -> tuple[dict[str, SegmentEdge], dict[SegmentEdge, dict[str, float]], dict[str, float]]:
        distances: dict[str, float] = {origin_stop_id: 0.0}
        previous_edge_by_stop: dict[str, SegmentEdge] = {}
        edge_prediction_cache: dict[SegmentEdge, dict[str, float]] = {}
        scored_stop_cache: set[str] = set()

        heap: list[tuple[float, str]] = [(0.0, origin_stop_id)]

        while heap:
            current_distance, current_stop_id = heapq.heappop(heap)

            if current_distance > distances.get(current_stop_id, float("inf")):
                continue
            if current_stop_id == destination_stop_id:
                break

            outgoing_edges = graph.get_outgoing_edges(current_stop_id)
            if not outgoing_edges:
                continue

            if current_stop_id not in scored_stop_cache:
                self._score_outgoing_edges(
                    outgoing_edges,
                    edge_prediction_cache,
                    query_timestamp_unix,
                )
                scored_stop_cache.add(current_stop_id)

            for edge in outgoing_edges:
                prediction = edge_prediction_cache[edge]
                edge_weight = max(
                    prediction["predicted_actual_segment_minutes"],
                    MIN_EDGE_WEIGHT_MINUTES,
                )
                candidate_distance = current_distance + edge_weight
                if candidate_distance < distances.get(edge.to_stop_id, float("inf")):
                    distances[edge.to_stop_id] = candidate_distance
                    previous_edge_by_stop[edge.to_stop_id] = edge
                    heapq.heappush(heap, (candidate_distance, edge.to_stop_id))

        return previous_edge_by_stop, edge_prediction_cache, distances

    def _score_outgoing_edges(
        self,
        outgoing_edges: tuple[SegmentEdge, ...],
        edge_prediction_cache: dict[SegmentEdge, dict[str, float]],
        query_timestamp_unix: int,
    ) -> None:
        uncached_edges = [edge for edge in outgoing_edges if edge not in edge_prediction_cache]
        if not uncached_edges:
            return

        segment_records = [
            self._build_segment_record(edge, query_timestamp_unix)
            for edge in uncached_edges
        ]
        predictions = self.prediction_service.predict_segments(segment_records)
        for edge, prediction in zip(uncached_edges, predictions, strict=True):
            edge_prediction_cache[edge] = prediction

    def _build_segment_record(
        self,
        edge: SegmentEdge,
        query_timestamp_unix: int,
    ) -> dict[str, str | int | float]:
        prev_segment_delay = 0.0
        rolling_segment_delay_3 = 0.0
        if self.realtime_enrichment_service:
            live_context = self.realtime_enrichment_service.get_segment_live_context(
                edge.route_id,
                edge.from_stop_id,
                edge.to_stop_id,
                reference_timestamp=query_timestamp_unix,
            )
            if live_context:
                prev_segment_delay = live_context.prev_segment_delay
                rolling_segment_delay_3 = live_context.rolling_segment_delay_3

        return {
            "route_id": edge.route_id,
            "from_stop_id": edge.from_stop_id,
            "to_stop_id": edge.to_stop_id,
            "stop_sequence": edge.stop_sequence,
            "normalized_stop_position": edge.normalized_stop_position,
            "distance_to_prev_stop_km": edge.distance_to_prev_stop_km,
            "segment_start_scheduled_unix": query_timestamp_unix,
            "scheduled_segment_minutes": edge.scheduled_segment_minutes,
            "prev_segment_delay": prev_segment_delay,
            "rolling_segment_delay_3": rolling_segment_delay_3,
        }

    def _reconstruct_edges(
        self,
        previous_edge_by_stop: dict[str, SegmentEdge],
        destination_stop_id: str,
    ) -> list[SegmentEdge]:
        route_edges: list[SegmentEdge] = []
        current_stop_id = destination_stop_id

        while current_stop_id in previous_edge_by_stop:
            edge = previous_edge_by_stop[current_stop_id]
            route_edges.append(edge)
            current_stop_id = edge.from_stop_id

        route_edges.reverse()
        return route_edges

    def _build_stop_path(
        self,
        graph: StaticTransitGraph,
        origin_stop_id: str,
        route_edges: list[SegmentEdge],
    ) -> list[dict[str, str | float]]:
        stop_ids = [origin_stop_id] + [edge.to_stop_id for edge in route_edges]
        stops = []
        for stop_id in stop_ids:
            stop = graph.stops_by_id[stop_id]
            stops.append(
                {
                    "stop_id": stop.stop_id,
                    "stop_name": stop.stop_name,
                    "stop_lat": stop.stop_lat,
                    "stop_lon": stop.stop_lon,
                }
            )
        return stops

    def _build_segment_predictions(
        self,
        route_edges: list[SegmentEdge],
        edge_prediction_cache: dict[SegmentEdge, dict[str, float]],
    ) -> list[dict[str, str | int | float]]:
        return [
            {
                "route_id": edge.route_id,
                "from_stop_id": edge.from_stop_id,
                "to_stop_id": edge.to_stop_id,
                "stop_sequence": edge.stop_sequence,
                "normalized_stop_position": edge.normalized_stop_position,
                "distance_to_prev_stop_km": edge.distance_to_prev_stop_km,
                "scheduled_segment_minutes": edge.scheduled_segment_minutes,
                "predicted_actual_segment_minutes": edge_prediction_cache[edge][
                    "predicted_actual_segment_minutes"
                ],
                "predicted_segment_delay_minutes": edge_prediction_cache[edge][
                    "predicted_segment_delay_minutes"
                ],
            }
            for edge in route_edges
        ]
