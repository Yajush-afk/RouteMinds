from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import count

from api.app.core.exceptions import RouteNotFoundException, StopNotFoundException
from api.app.services.gtfs_graph_service import (
    GTFSGraphService,
    SegmentEdge,
    StaticTransitGraph,
)
from api.app.services.prediction_service import PredictionService
from api.app.services.realtime_enrichment_service import RealtimeEnrichmentService

MIN_EDGE_WEIGHT_MINUTES = 0.01
TRANSFER_BUFFER_MINUTES = 5.0


@dataclass(frozen=True, slots=True)
class RouteOptimizationResult:
    stops: list[dict[str, str | float]]
    segments: list[dict[str, str | int | float]]
    total_predicted_eta_minutes: float


@dataclass(frozen=True, slots=True)
class RouteState:
    stop_id: str
    active_route_id: str | None


@dataclass(frozen=True, slots=True)
class RouteStep:
    from_state: RouteState
    to_state: RouteState
    edge: SegmentEdge
    scheduled_departure_unix: int
    wait_minutes_before_boarding: float


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

        (
            previous_step_by_state,
            edge_prediction_cache,
            distances,
            best_destination_state,
        ) = self._run_dijkstra(
            graph,
            origin_stop_key,
            destination_stop_key,
            query_timestamp_unix,
        )

        if best_destination_state is None:
            raise RouteNotFoundException(origin_stop_key, destination_stop_key)

        route_edges = self._reconstruct_edges(previous_step_by_state, best_destination_state)
        stops = self._build_stop_path(graph, origin_stop_key, route_edges)
        segments = self._build_segment_predictions(route_edges, edge_prediction_cache)

        return RouteOptimizationResult(
            stops=stops,
            segments=segments,
            total_predicted_eta_minutes=float(distances[best_destination_state]),
        )

    def _run_dijkstra(
        self,
        graph: StaticTransitGraph,
        origin_stop_id: str,
        destination_stop_id: str,
        query_timestamp_unix: int,
    ) -> tuple[
        dict[RouteState, RouteStep],
        dict[tuple[SegmentEdge, int], dict[str, float]],
        dict[RouteState, float],
        RouteState | None,
    ]:
        origin_state = RouteState(stop_id=origin_stop_id, active_route_id=None)
        distances: dict[RouteState, float] = {origin_state: 0.0}
        arrival_timestamps: dict[RouteState, int] = {origin_state: query_timestamp_unix}
        previous_step_by_state: dict[RouteState, RouteStep] = {}
        edge_prediction_cache: dict[tuple[SegmentEdge, int], dict[str, float]] = {}

        priority_sequence = count()
        heap: list[tuple[float, int, RouteState]] = [
            (0.0, next(priority_sequence), origin_state)
        ]
        best_destination_state: RouteState | None = None

        while heap:
            current_distance, _, current_state = heapq.heappop(heap)

            if current_distance > distances.get(current_state, float("inf")):
                continue

            current_arrival_timestamp = arrival_timestamps[current_state]
            if current_state.stop_id == destination_stop_id:
                best_destination_state = current_state
                break

            outgoing_edges = graph.get_outgoing_edges(current_state.stop_id)
            if not outgoing_edges:
                continue

            edge_departure_timestamps = self._resolve_edge_departure_timestamps(
                outgoing_edges,
                current_state=current_state,
                current_arrival_timestamp=current_arrival_timestamp,
            )
            if not edge_departure_timestamps:
                continue

            self._score_outgoing_edges(edge_departure_timestamps, edge_prediction_cache)

            for edge in outgoing_edges:
                departure_timestamp = edge_departure_timestamps.get(edge)
                if departure_timestamp is None:
                    continue

                prediction_cache_key = (edge, departure_timestamp)
                prediction = edge_prediction_cache[prediction_cache_key]
                edge_weight = max(
                    prediction["predicted_actual_segment_minutes"],
                    MIN_EDGE_WEIGHT_MINUTES,
                )
                wait_minutes_before_boarding = max(
                    0.0,
                    (departure_timestamp - current_arrival_timestamp) / 60.0,
                )
                candidate_distance = (
                    current_distance + wait_minutes_before_boarding + edge_weight
                )
                next_state = RouteState(
                    stop_id=edge.to_stop_id,
                    active_route_id=edge.route_id,
                )
                if candidate_distance < distances.get(next_state, float("inf")):
                    distances[next_state] = candidate_distance
                    arrival_timestamps[next_state] = departure_timestamp + int(
                        round(edge_weight * 60.0)
                    )
                    previous_step_by_state[next_state] = RouteStep(
                        from_state=current_state,
                        to_state=next_state,
                        edge=edge,
                        scheduled_departure_unix=departure_timestamp,
                        wait_minutes_before_boarding=wait_minutes_before_boarding,
                    )
                    heapq.heappush(
                        heap,
                        (candidate_distance, next(priority_sequence), next_state),
                    )

        return (
            previous_step_by_state,
            edge_prediction_cache,
            distances,
            best_destination_state,
        )

    def _resolve_edge_departure_timestamps(
        self,
        outgoing_edges: tuple[SegmentEdge, ...],
        *,
        current_state: RouteState,
        current_arrival_timestamp: int,
    ) -> dict[SegmentEdge, int]:
        departure_timestamps: dict[SegmentEdge, int] = {}
        for edge in outgoing_edges:
            transfer_buffer_minutes = self._transfer_buffer_minutes(
                current_route_id=current_state.active_route_id,
                next_route_id=edge.route_id,
            )
            earliest_board_timestamp = current_arrival_timestamp + int(
                round(transfer_buffer_minutes * 60.0)
            )
            departure_timestamp = edge.get_next_departure_unix(earliest_board_timestamp)
            if departure_timestamp is None:
                continue
            departure_timestamps[edge] = departure_timestamp
        return departure_timestamps

    def _score_outgoing_edges(
        self,
        edge_departure_timestamps: dict[SegmentEdge, int],
        edge_prediction_cache: dict[tuple[SegmentEdge, int], dict[str, float]],
    ) -> None:
        uncached_edges = [
            (edge, departure_timestamp)
            for edge, departure_timestamp in edge_departure_timestamps.items()
            if (edge, departure_timestamp) not in edge_prediction_cache
        ]
        if not uncached_edges:
            return

        segment_records = [
            self._build_segment_record(edge, departure_timestamp)
            for edge, departure_timestamp in uncached_edges
        ]
        predictions = self.prediction_service.predict_segments(segment_records)
        for (edge, departure_timestamp), prediction in zip(
            uncached_edges,
            predictions,
            strict=True,
        ):
            edge_prediction_cache[(edge, departure_timestamp)] = prediction

    def _transfer_buffer_minutes(
        self,
        *,
        current_route_id: str | None,
        next_route_id: str,
    ) -> float:
        if current_route_id is None or current_route_id == next_route_id:
            return 0.0
        return TRANSFER_BUFFER_MINUTES

    def _build_segment_record(
        self,
        edge: SegmentEdge,
        departure_timestamp: int,
    ) -> dict[str, str | int | float]:
        prev_segment_delay = 0.0
        rolling_segment_delay_3 = 0.0
        if self.realtime_enrichment_service:
            live_context = self.realtime_enrichment_service.get_segment_live_context(
                edge.route_id,
                edge.from_stop_id,
                edge.to_stop_id,
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
            "segment_start_scheduled_unix": departure_timestamp,
            "scheduled_segment_minutes": edge.scheduled_segment_minutes,
            "prev_segment_delay": prev_segment_delay,
            "rolling_segment_delay_3": rolling_segment_delay_3,
        }

    def _reconstruct_edges(
        self,
        previous_step_by_state: dict[RouteState, RouteStep],
        destination_state: RouteState,
    ) -> list[RouteStep]:
        route_steps: list[RouteStep] = []
        current_state = destination_state

        while current_state in previous_step_by_state:
            step = previous_step_by_state[current_state]
            route_steps.append(step)
            current_state = step.from_state

        route_steps.reverse()
        return route_steps

    def _build_stop_path(
        self,
        graph: StaticTransitGraph,
        origin_stop_id: str,
        route_steps: list[RouteStep],
    ) -> list[dict[str, str | float]]:
        stop_ids = [origin_stop_id] + [step.edge.to_stop_id for step in route_steps]
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
        route_steps: list[RouteStep],
        edge_prediction_cache: dict[tuple[SegmentEdge, int], dict[str, float]],
    ) -> list[dict[str, str | int | float]]:
        return [
            {
                "route_id": step.edge.route_id,
                "from_stop_id": step.edge.from_stop_id,
                "to_stop_id": step.edge.to_stop_id,
                "scheduled_departure_unix": step.scheduled_departure_unix,
                "stop_sequence": step.edge.stop_sequence,
                "normalized_stop_position": step.edge.normalized_stop_position,
                "distance_to_prev_stop_km": step.edge.distance_to_prev_stop_km,
                "scheduled_segment_minutes": step.edge.scheduled_segment_minutes,
                "wait_minutes_before_boarding": step.wait_minutes_before_boarding,
                "predicted_actual_segment_minutes": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ][
                    "predicted_actual_segment_minutes"
                ],
                "predicted_segment_delay_minutes": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ][
                    "predicted_segment_delay_minutes"
                ],
            }
            for step in route_steps
        ]
