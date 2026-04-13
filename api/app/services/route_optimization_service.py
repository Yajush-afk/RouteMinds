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
MAX_RELIABILITY_PENALTY_MINUTES = 3.0


@dataclass(frozen=True, slots=True)
class RouteOptimizationResult:
    stops: list[dict[str, str | float]]
    segments: list[dict[str, str | int | float]]
    total_predicted_eta_minutes: float
    predicted_eta_lower_minutes: float
    predicted_eta_upper_minutes: float
    route_reliability_score: float


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
    scheduled_wait_minutes_before_boarding: float
    wait_minutes_before_boarding: float
    boarding_feasibility_score: float


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
                predicted_eta_lower_minutes=0.0,
                predicted_eta_upper_minutes=0.0,
                route_reliability_score=1.0,
            )

        (
            previous_step_by_state,
            edge_prediction_cache,
            generalized_costs,
            etas,
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
        route_summary = self._build_route_summary(segments)

        return RouteOptimizationResult(
            stops=stops,
            segments=segments,
            total_predicted_eta_minutes=float(etas[best_destination_state]),
            predicted_eta_lower_minutes=route_summary["predicted_eta_lower_minutes"],
            predicted_eta_upper_minutes=route_summary["predicted_eta_upper_minutes"],
            route_reliability_score=route_summary["route_reliability_score"],
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
        dict[RouteState, float],
        RouteState | None,
    ]:
        origin_state = RouteState(stop_id=origin_stop_id, active_route_id=None)
        generalized_costs: dict[RouteState, float] = {origin_state: 0.0}
        etas: dict[RouteState, float] = {origin_state: 0.0}
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

            if current_distance > generalized_costs.get(current_state, float("inf")):
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
                    float(prediction["predicted_actual_segment_minutes"]),
                    MIN_EDGE_WEIGHT_MINUTES,
                )
                scheduled_wait_minutes_before_boarding = max(
                    0.0,
                    (departure_timestamp - current_arrival_timestamp) / 60.0,
                )
                (
                    wait_minutes_before_boarding,
                    boarding_feasibility_score,
                ) = self._estimate_wait_and_boarding(
                    edge=edge,
                    current_state=current_state,
                    current_arrival_timestamp=current_arrival_timestamp,
                    scheduled_wait_minutes=scheduled_wait_minutes_before_boarding,
                )
                reliability_penalty_minutes = self._reliability_penalty_minutes(
                    prediction=prediction,
                    boarding_feasibility_score=boarding_feasibility_score,
                )
                candidate_eta = (
                    etas[current_state] + wait_minutes_before_boarding + edge_weight
                )
                candidate_distance = (
                    current_distance
                    + wait_minutes_before_boarding
                    + edge_weight
                    + reliability_penalty_minutes
                )
                next_state = RouteState(
                    stop_id=edge.to_stop_id,
                    active_route_id=edge.route_id,
                )
                if candidate_distance < generalized_costs.get(next_state, float("inf")):
                    generalized_costs[next_state] = candidate_distance
                    etas[next_state] = candidate_eta
                    arrival_timestamps[next_state] = departure_timestamp + int(
                        round(edge_weight * 60.0)
                    )
                    previous_step_by_state[next_state] = RouteStep(
                        from_state=current_state,
                        to_state=next_state,
                        edge=edge,
                        scheduled_departure_unix=departure_timestamp,
                        scheduled_wait_minutes_before_boarding=(
                            scheduled_wait_minutes_before_boarding
                        ),
                        wait_minutes_before_boarding=wait_minutes_before_boarding,
                        boarding_feasibility_score=boarding_feasibility_score,
                    )
                    heapq.heappush(
                        heap,
                        (candidate_distance, next(priority_sequence), next_state),
                    )

        return (
            previous_step_by_state,
            edge_prediction_cache,
            generalized_costs,
            etas,
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
        route_delay_minutes_live = 0.0
        segment_slowdown_index = 1.0
        corridor_slowdown_score_live = 1.0
        bunching_indicator = 0.0
        headway_irregularity_score_live = 0.0
        stop_recent_arrival_gap_minutes = 0.0
        if self.realtime_enrichment_service:
            live_context = self.realtime_enrichment_service.get_segment_live_context(
                edge.route_id,
                edge.from_stop_id,
                edge.to_stop_id,
            )
            if live_context:
                prev_segment_delay = live_context.prev_segment_delay
                rolling_segment_delay_3 = live_context.rolling_segment_delay_3
                route_delay_minutes_live = live_context.route_delay_minutes_live
                segment_slowdown_index = live_context.segment_slowdown_index
                corridor_slowdown_score_live = (
                    live_context.corridor_slowdown_score_live
                )
                bunching_indicator = live_context.bunching_indicator
                headway_irregularity_score_live = (
                    live_context.headway_irregularity_score_live
                )
                stop_recent_arrival_gap_minutes = (
                    live_context.stop_recent_arrival_gap_minutes
                )

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
            "route_delay_minutes_live": route_delay_minutes_live,
            "segment_slowdown_index": segment_slowdown_index,
            "corridor_slowdown_score_live": corridor_slowdown_score_live,
            "bunching_indicator": bunching_indicator,
            "headway_irregularity_score_live": headway_irregularity_score_live,
            "stop_recent_arrival_gap_minutes": stop_recent_arrival_gap_minutes,
        }

    def _estimate_wait_and_boarding(
        self,
        *,
        edge: SegmentEdge,
        current_state: RouteState,
        current_arrival_timestamp: int,
        scheduled_wait_minutes: float,
    ) -> tuple[float, float]:
        expected_wait_minutes = scheduled_wait_minutes
        headway_irregularity_score_live = 0.0
        bunching_indicator = 0.0
        rolling_route_delay_minutes = 0.0

        if not self.realtime_enrichment_service:
            return expected_wait_minutes, 1.0

        stop_context = self.realtime_enrichment_service.get_stop_live_context(
            edge.route_id,
            edge.from_stop_id,
            reference_timestamp=current_arrival_timestamp,
        )
        route_context = self.realtime_enrichment_service.get_route_live_context(
            edge.route_id,
            reference_timestamp=current_arrival_timestamp,
        )
        scheduled_headway_minutes = (
            self.realtime_enrichment_service.get_scheduled_headway_minutes(
                edge.route_id,
                edge.from_stop_id,
            )
        )

        if stop_context:
            headway_irregularity_score_live = (
                stop_context.headway_irregularity_score_live
            )
            bunching_indicator = stop_context.bunching_indicator

        if route_context:
            rolling_route_delay_minutes = route_context.rolling_route_delay_minutes

        if scheduled_headway_minutes and scheduled_headway_minutes <= 15.0:
            headway_based_wait_minutes = scheduled_headway_minutes / 2.0
            if stop_context and stop_context.recent_arrival_gap_minutes > 0.0:
                headway_based_wait_minutes = max(
                    headway_based_wait_minutes,
                    stop_context.recent_arrival_gap_minutes / 2.0,
                )
            expected_wait_minutes = max(expected_wait_minutes, headway_based_wait_minutes)

        instability_penalty_minutes = 0.0
        if stop_context:
            instability_penalty_minutes += min(
                4.0,
                headway_irregularity_score_live * max(1.0, expected_wait_minutes * 0.5),
            )
            instability_penalty_minutes += min(1.5, bunching_indicator)

        if route_context and rolling_route_delay_minutes > 0.0:
            instability_penalty_minutes += min(5.0, rolling_route_delay_minutes / 6.0)

        if current_state.active_route_id is not None and current_state.active_route_id != edge.route_id:
            instability_penalty_minutes += 1.0

        expected_wait_minutes = max(
            scheduled_wait_minutes,
            expected_wait_minutes + instability_penalty_minutes,
        )

        boarding_feasibility_score = 1.0 - min(
            0.95,
            (expected_wait_minutes / 20.0) * 0.45
            + min(1.0, headway_irregularity_score_live) * 0.3
            + min(1.0, bunching_indicator) * 0.15
            + min(1.0, max(0.0, rolling_route_delay_minutes) / 20.0) * 0.1,
        )
        return expected_wait_minutes, max(0.05, boarding_feasibility_score)

    def _reliability_penalty_minutes(
        self,
        *,
        prediction: dict[str, float],
        boarding_feasibility_score: float,
    ) -> float:
        segment_uncertainty = max(0.0, float(prediction.get("segment_uncertainty", 0.0)))
        segment_reliability_score = float(
            prediction.get("segment_reliability_score", 1.0)
        )
        instability = (1.0 - max(0.0, min(1.0, segment_reliability_score))) + (
            1.0 - max(0.0, min(1.0, boarding_feasibility_score))
        )
        penalty = (segment_uncertainty * 0.25) + (instability * 1.25)
        return min(MAX_RELIABILITY_PENALTY_MINUTES, penalty)

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
                "scheduled_wait_minutes_before_boarding": step.scheduled_wait_minutes_before_boarding,
                "wait_minutes_before_boarding": step.wait_minutes_before_boarding,
                "boarding_feasibility_score": step.boarding_feasibility_score,
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
                "segment_uncertainty": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("segment_uncertainty", 0.0),
                "segment_reliability_score": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("segment_reliability_score", 1.0),
                "predicted_eta_lower_minutes": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get(
                    "predicted_eta_lower_minutes",
                    edge_prediction_cache[(step.edge, step.scheduled_departure_unix)][
                        "predicted_actual_segment_minutes"
                    ],
                ),
                "predicted_eta_upper_minutes": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get(
                    "predicted_eta_upper_minutes",
                    edge_prediction_cache[(step.edge, step.scheduled_departure_unix)][
                        "predicted_actual_segment_minutes"
                    ],
                ),
            }
            for step in route_steps
        ]

    def _build_route_summary(
        self,
        segments: list[dict[str, str | int | float]],
    ) -> dict[str, float]:
        if not segments:
            return {
                "predicted_eta_lower_minutes": 0.0,
                "predicted_eta_upper_minutes": 0.0,
                "route_reliability_score": 1.0,
            }

        total_wait = sum(float(segment["wait_minutes_before_boarding"]) for segment in segments)
        total_lower = total_wait + sum(
            float(segment["predicted_eta_lower_minutes"]) for segment in segments
        )
        total_upper = total_wait + sum(
            float(segment["predicted_eta_upper_minutes"]) for segment in segments
        )
        reliability_weight_sum = 0.0
        weighted_reliability = 0.0
        for segment in segments:
            segment_weight = (
                float(segment["predicted_actual_segment_minutes"])
                + float(segment["wait_minutes_before_boarding"])
            )
            segment_reliability = float(segment.get("segment_reliability_score", 1.0))
            boarding_feasibility = float(segment.get("boarding_feasibility_score", 1.0))
            combined_reliability = max(
                0.05,
                min(0.99, (segment_reliability * 0.7) + (boarding_feasibility * 0.3)),
            )
            reliability_weight_sum += segment_weight
            weighted_reliability += combined_reliability * segment_weight

        route_reliability_score = (
            weighted_reliability / reliability_weight_sum
            if reliability_weight_sum > 0.0
            else 1.0
        )
        return {
            "predicted_eta_lower_minutes": max(0.0, total_lower),
            "predicted_eta_upper_minutes": max(total_lower, total_upper),
            "route_reliability_score": max(0.05, min(0.99, route_reliability_score)),
        }
