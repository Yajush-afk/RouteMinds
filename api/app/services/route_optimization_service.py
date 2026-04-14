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
TRANSFER_PENALTY_MINUTES = 2.0
MAX_UNCERTAINTY_PENALTY_MINUTES = 2.5
MAX_RELIABILITY_PENALTY_MINUTES = 2.0
MAX_UNSTABLE_CORRIDOR_PENALTY_MINUTES = 2.5
MAX_DETOUR_PENALTY_MINUTES = 1.5
MAX_FRAGILE_TRANSFER_PENALTY_MINUTES = 3.0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    travel_time_cost: float
    waiting_time_cost: float
    transfer_penalty_cost: float
    uncertainty_penalty_cost: float
    reliability_penalty_cost: float
    unstable_corridor_penalty_cost: float
    detour_penalty_cost: float
    fragile_transfer_penalty_cost: float
    generalized_cost: float


@dataclass(frozen=True, slots=True)
class TransferAssessment:
    is_transfer: bool
    transfer_buffer_minutes: float
    transfer_slack_minutes: float
    transfer_wait_uncertainty_minutes: float
    missed_transfer_risk: float
    is_fragile_transfer: bool
    fragile_transfer_penalty_cost: float


@dataclass(frozen=True, slots=True)
class RouteOptimizationResult:
    stops: list[dict[str, str | float]]
    segments: list[dict[str, str | int | float]]
    total_predicted_eta_minutes: float
    predicted_eta_lower_minutes: float
    predicted_eta_upper_minutes: float
    route_reliability_score: float
    generalized_cost_minutes: float
    cost_breakdown: dict[str, float]
    total_wait_minutes: float
    total_in_vehicle_minutes: float
    transfer_count: int
    fragile_transfer_count: int
    transfer_fragility_score: float
    congestion_proxy_ratio: float
    congestion_proxy_percent: float
    service_quality_score: float
    selection_reasons: list[str]
    explanation_summary: str
    alternatives: list[dict[str, str | float]]


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
    transfer_assessment: TransferAssessment
    cost_breakdown: CostBreakdown


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
                generalized_cost_minutes=0.0,
                cost_breakdown={
                    "travel_time_cost": 0.0,
                    "waiting_time_cost": 0.0,
                    "transfer_penalty_cost": 0.0,
                    "uncertainty_penalty_cost": 0.0,
                    "reliability_penalty_cost": 0.0,
                    "unstable_corridor_penalty_cost": 0.0,
                    "detour_penalty_cost": 0.0,
                    "fragile_transfer_penalty_cost": 0.0,
                    "generalized_cost": 0.0,
                },
                total_wait_minutes=0.0,
                total_in_vehicle_minutes=0.0,
                transfer_count=0,
                fragile_transfer_count=0,
                transfer_fragility_score=0.0,
                congestion_proxy_ratio=1.0,
                congestion_proxy_percent=0.0,
                service_quality_score=1.0,
                selection_reasons=["Origin and destination are the same stop."],
                explanation_summary="No travel is required for this query.",
                alternatives=[],
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
            generalized_cost_minutes=float(generalized_costs[best_destination_state]),
            cost_breakdown=route_summary["cost_breakdown"],
            total_wait_minutes=route_summary["total_wait_minutes"],
            total_in_vehicle_minutes=route_summary["total_in_vehicle_minutes"],
            transfer_count=route_summary["transfer_count"],
            fragile_transfer_count=route_summary["fragile_transfer_count"],
            transfer_fragility_score=route_summary["transfer_fragility_score"],
            congestion_proxy_ratio=route_summary["congestion_proxy_ratio"],
            congestion_proxy_percent=route_summary["congestion_proxy_percent"],
            service_quality_score=route_summary["service_quality_score"],
            selection_reasons=route_summary["selection_reasons"],
            explanation_summary=route_summary["explanation_summary"],
            alternatives=[],
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
                transfer_assessment = self._transfer_assessment(
                    edge=edge,
                    current_state=current_state,
                    prediction=prediction,
                    scheduled_wait_minutes=scheduled_wait_minutes_before_boarding,
                    boarding_feasibility_score=boarding_feasibility_score,
                )
                cost_breakdown = self._generalized_cost_breakdown(
                    edge=edge,
                    current_state=current_state,
                    prediction=prediction,
                    travel_time_minutes=edge_weight,
                    wait_minutes=wait_minutes_before_boarding,
                    reliability_penalty_minutes=reliability_penalty_minutes,
                    boarding_feasibility_score=boarding_feasibility_score,
                    transfer_assessment=transfer_assessment,
                )
                candidate_eta = (
                    etas[current_state] + wait_minutes_before_boarding + edge_weight
                )
                candidate_distance = current_distance + cost_breakdown.generalized_cost
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
                        transfer_assessment=transfer_assessment,
                        cost_breakdown=cost_breakdown,
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
        for (edge, departure_timestamp), prediction, segment_record in zip(
            uncached_edges,
            predictions,
            segment_records,
            strict=True,
        ):
            edge_prediction_cache[(edge, departure_timestamp)] = {
                **segment_record,
                **prediction,
            }

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
        corridor_instability_score_live = 0.0
        service_quality_score = 1.0
        persistent_unreliability_penalty = 0.0
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
                corridor_instability_score_live = getattr(
                    live_context,
                    "corridor_instability_score_live",
                    0.0,
                )
                service_quality_score = getattr(
                    live_context,
                    "service_quality_score",
                    1.0,
                )
                persistent_unreliability_penalty = getattr(
                    live_context,
                    "persistent_unreliability_penalty",
                    0.0,
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
            "corridor_instability_score_live": corridor_instability_score_live,
            "service_quality_score": service_quality_score,
            "persistent_unreliability_penalty": persistent_unreliability_penalty,
            "bunching_indicator": bunching_indicator,
            "headway_irregularity_score_live": headway_irregularity_score_live,
            "stop_recent_arrival_gap_minutes": stop_recent_arrival_gap_minutes,
        }

    def _generalized_cost_breakdown(
        self,
        *,
        edge: SegmentEdge,
        current_state: RouteState,
        prediction: dict[str, float],
        travel_time_minutes: float,
        wait_minutes: float,
        reliability_penalty_minutes: float,
        boarding_feasibility_score: float,
        transfer_assessment: TransferAssessment,
    ) -> CostBreakdown:
        transfer_penalty_cost = self._transfer_penalty_cost(
            current_route_id=current_state.active_route_id,
            next_route_id=edge.route_id,
        )
        uncertainty_penalty_cost = self._uncertainty_penalty_minutes(prediction=prediction)
        unstable_corridor_penalty_cost = self._unstable_corridor_penalty_minutes(
            prediction=prediction,
        )
        detour_penalty_cost = self._detour_penalty_minutes(edge=edge)
        fragile_transfer_penalty_cost = transfer_assessment.fragile_transfer_penalty_cost
        generalized_cost = (
            travel_time_minutes
            + wait_minutes
            + transfer_penalty_cost
            + uncertainty_penalty_cost
            + reliability_penalty_minutes
            + unstable_corridor_penalty_cost
            + detour_penalty_cost
            + fragile_transfer_penalty_cost
        )
        return CostBreakdown(
            travel_time_cost=travel_time_minutes,
            waiting_time_cost=wait_minutes,
            transfer_penalty_cost=transfer_penalty_cost,
            uncertainty_penalty_cost=uncertainty_penalty_cost,
            reliability_penalty_cost=reliability_penalty_minutes,
            unstable_corridor_penalty_cost=unstable_corridor_penalty_cost,
            detour_penalty_cost=detour_penalty_cost,
            fragile_transfer_penalty_cost=fragile_transfer_penalty_cost,
            generalized_cost=generalized_cost,
        )

    def _transfer_assessment(
        self,
        *,
        edge: SegmentEdge,
        current_state: RouteState,
        prediction: dict[str, float],
        scheduled_wait_minutes: float,
        boarding_feasibility_score: float,
    ) -> TransferAssessment:
        transfer_buffer_minutes = self._transfer_buffer_minutes(
            current_route_id=current_state.active_route_id,
            next_route_id=edge.route_id,
        )
        is_transfer = transfer_buffer_minutes > 0.0
        transfer_slack_minutes = max(0.0, scheduled_wait_minutes - transfer_buffer_minutes)
        transfer_wait_uncertainty_minutes = min(
            4.0,
            max(0.0, float(prediction.get("segment_uncertainty", 0.0))) * 0.35
            + max(0.0, float(prediction.get("headway_irregularity_score_live", 0.0))) * 1.4
            + max(0.0, float(prediction.get("bunching_indicator", 0.0))) * 0.75,
        )
        if not is_transfer:
            return TransferAssessment(
                is_transfer=False,
                transfer_buffer_minutes=0.0,
                transfer_slack_minutes=0.0,
                transfer_wait_uncertainty_minutes=0.0,
                missed_transfer_risk=0.0,
                is_fragile_transfer=False,
                fragile_transfer_penalty_cost=0.0,
            )

        slack_pressure = max(0.0, 2.5 - transfer_slack_minutes) / 2.5
        instability_pressure = 1.0 - max(0.05, min(1.0, boarding_feasibility_score))
        missed_transfer_risk = _clamp(
            slack_pressure * 0.45
            + instability_pressure * 0.35
            + min(1.0, transfer_wait_uncertainty_minutes / 4.0) * 0.2,
            0.0,
            0.99,
        )
        fragile_transfer_penalty_cost = min(
            MAX_FRAGILE_TRANSFER_PENALTY_MINUTES,
            max(0.0, 2.0 - transfer_slack_minutes) * 0.8
            + missed_transfer_risk * 1.6
            + transfer_wait_uncertainty_minutes * 0.25,
        )
        is_fragile_transfer = transfer_slack_minutes < 2.0 or missed_transfer_risk >= 0.45
        return TransferAssessment(
            is_transfer=True,
            transfer_buffer_minutes=transfer_buffer_minutes,
            transfer_slack_minutes=transfer_slack_minutes,
            transfer_wait_uncertainty_minutes=transfer_wait_uncertainty_minutes,
            missed_transfer_risk=missed_transfer_risk,
            is_fragile_transfer=is_fragile_transfer,
            fragile_transfer_penalty_cost=fragile_transfer_penalty_cost,
        )

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

    def _transfer_penalty_cost(
        self,
        *,
        current_route_id: str | None,
        next_route_id: str,
    ) -> float:
        if current_route_id is None or current_route_id == next_route_id:
            return 0.0
        return TRANSFER_PENALTY_MINUTES

    def _uncertainty_penalty_minutes(self, *, prediction: dict[str, float]) -> float:
        segment_uncertainty = max(0.0, float(prediction.get("segment_uncertainty", 0.0)))
        return min(MAX_UNCERTAINTY_PENALTY_MINUTES, segment_uncertainty * 0.35)

    def _unstable_corridor_penalty_minutes(
        self,
        *,
        prediction: dict[str, float],
    ) -> float:
        corridor_slowdown = max(
            0.0,
            float(prediction.get("corridor_slowdown_score_live", 1.0)) - 1.0,
        )
        corridor_instability = max(
            0.0,
            float(prediction.get("corridor_instability_score_live", 0.0)),
        )
        persistent_unreliability_penalty = max(
            0.0,
            float(prediction.get("persistent_unreliability_penalty", 0.0)),
        )
        segment_slowdown = max(
            0.0,
            float(prediction.get("segment_slowdown_index", 1.0)) - 1.0,
        )
        headway_irregularity = max(
            0.0,
            float(prediction.get("headway_irregularity_score_live", 0.0)),
        )
        bunching_indicator = max(0.0, float(prediction.get("bunching_indicator", 0.0)))
        route_delay = max(0.0, float(prediction.get("route_delay_minutes_live", 0.0)))
        penalty = 0.0
        penalty += min(1.0, corridor_slowdown * 1.1)
        penalty += min(0.7, corridor_instability * 0.9)
        penalty += min(0.6, persistent_unreliability_penalty * 0.5)
        penalty += min(0.8, segment_slowdown * 0.8)
        penalty += min(0.4, headway_irregularity * 0.5)
        penalty += min(0.2, bunching_indicator * 0.2)
        penalty += min(0.4, route_delay / 15.0)
        return min(MAX_UNSTABLE_CORRIDOR_PENALTY_MINUTES, penalty)

    def _detour_penalty_minutes(self, *, edge: SegmentEdge) -> float:
        excess_distance = max(0.0, edge.distance_to_prev_stop_km - 2.0)
        return min(MAX_DETOUR_PENALTY_MINUTES, excess_distance * 0.35)

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
                "is_transfer": step.transfer_assessment.is_transfer,
                "transfer_buffer_minutes": step.transfer_assessment.transfer_buffer_minutes,
                "transfer_slack_minutes": step.transfer_assessment.transfer_slack_minutes,
                "transfer_wait_uncertainty_minutes": step.transfer_assessment.transfer_wait_uncertainty_minutes,
                "missed_transfer_risk": step.transfer_assessment.missed_transfer_risk,
                "is_fragile_transfer": step.transfer_assessment.is_fragile_transfer,
                "travel_time_cost": step.cost_breakdown.travel_time_cost,
                "waiting_time_cost": step.cost_breakdown.waiting_time_cost,
                "transfer_penalty_cost": step.cost_breakdown.transfer_penalty_cost,
                "uncertainty_penalty_cost": step.cost_breakdown.uncertainty_penalty_cost,
                "reliability_penalty_cost": step.cost_breakdown.reliability_penalty_cost,
                "unstable_corridor_penalty_cost": step.cost_breakdown.unstable_corridor_penalty_cost,
                "detour_penalty_cost": step.cost_breakdown.detour_penalty_cost,
                "fragile_transfer_penalty_cost": step.cost_breakdown.fragile_transfer_penalty_cost,
                "generalized_cost": step.cost_breakdown.generalized_cost,
                "congestion_proxy_ratio": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("congestion_proxy_ratio", 1.0),
                "congestion_proxy_percent": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("congestion_proxy_percent", 0.0),
                "corridor_instability_score_live": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("corridor_instability_score_live", 0.0),
                "service_quality_score": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("service_quality_score", 1.0),
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

    def _selection_reasons(
        self,
        *,
        total_wait_minutes: float,
        route_reliability_score: float,
        transfer_count: int,
        fragile_transfer_count: int,
        congestion_proxy_ratio: float,
        service_quality_score: float,
    ) -> list[str]:
        reasons: list[str] = [
            "Chosen for the lowest generalized cost balancing ETA, wait time, and risk.",
        ]
        if total_wait_minutes <= 5.0:
            reasons.append("Low expected boarding and transfer wait time.")
        if route_reliability_score >= 0.8:
            reasons.append("High route reliability under current live conditions.")
        if transfer_count == 0:
            reasons.append("No route transfers required.")
        elif fragile_transfer_count == 0:
            reasons.append("Transfers are buffered and not considered fragile.")
        if congestion_proxy_ratio <= 1.1:
            reasons.append("Corridor slowdown is close to typical conditions.")
        if service_quality_score >= 0.75:
            reasons.append("Current route service quality is stable.")
        return reasons[:4]

    def _build_route_summary(
        self,
        segments: list[dict[str, str | int | float]],
    ) -> dict[str, float]:
        if not segments:
            return {
                "predicted_eta_lower_minutes": 0.0,
                "predicted_eta_upper_minutes": 0.0,
                "route_reliability_score": 1.0,
                "total_wait_minutes": 0.0,
                "total_in_vehicle_minutes": 0.0,
                "transfer_count": 0,
                "fragile_transfer_count": 0,
                "transfer_fragility_score": 0.0,
                "congestion_proxy_ratio": 1.0,
                "congestion_proxy_percent": 0.0,
                "service_quality_score": 1.0,
                "selection_reasons": ["No travel is required for this query."],
                "explanation_summary": "No travel is required for this query.",
                "cost_breakdown": {
                    "travel_time_cost": 0.0,
                    "waiting_time_cost": 0.0,
                    "transfer_penalty_cost": 0.0,
                    "uncertainty_penalty_cost": 0.0,
                    "reliability_penalty_cost": 0.0,
                    "unstable_corridor_penalty_cost": 0.0,
                    "detour_penalty_cost": 0.0,
                    "fragile_transfer_penalty_cost": 0.0,
                    "generalized_cost": 0.0,
                },
            }

        total_wait = sum(float(segment["wait_minutes_before_boarding"]) for segment in segments)
        total_in_vehicle = sum(float(segment["predicted_actual_segment_minutes"]) for segment in segments)
        total_lower = total_wait + sum(
            float(segment["predicted_eta_lower_minutes"]) for segment in segments
        )
        total_upper = total_wait + sum(
            float(segment["predicted_eta_upper_minutes"]) for segment in segments
        )
        reliability_weight_sum = 0.0
        weighted_reliability = 0.0
        congestion_weight_sum = 0.0
        weighted_congestion_ratio = 0.0
        weighted_service_quality = 0.0
        transfer_count = 0
        fragile_transfer_count = 0
        transfer_fragility_sum = 0.0
        cost_breakdown = {
            "travel_time_cost": 0.0,
            "waiting_time_cost": 0.0,
            "transfer_penalty_cost": 0.0,
            "uncertainty_penalty_cost": 0.0,
            "reliability_penalty_cost": 0.0,
            "unstable_corridor_penalty_cost": 0.0,
            "detour_penalty_cost": 0.0,
            "fragile_transfer_penalty_cost": 0.0,
            "generalized_cost": 0.0,
        }
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
            congestion_weight_sum += segment_weight
            weighted_congestion_ratio += float(segment.get("congestion_proxy_ratio", 1.0)) * segment_weight
            weighted_service_quality += float(segment.get("service_quality_score", 1.0)) * segment_weight
            if bool(segment.get("is_transfer", False)):
                transfer_count += 1
                transfer_fragility_sum += float(segment.get("missed_transfer_risk", 0.0))
                if bool(segment.get("is_fragile_transfer", False)):
                    fragile_transfer_count += 1
            for key in cost_breakdown:
                cost_breakdown[key] += float(segment.get(key, 0.0))

        route_reliability_score = (
            weighted_reliability / reliability_weight_sum
            if reliability_weight_sum > 0.0
            else 1.0
        )
        congestion_proxy_ratio = (
            weighted_congestion_ratio / congestion_weight_sum
            if congestion_weight_sum > 0.0
            else 1.0
        )
        service_quality_score = (
            weighted_service_quality / congestion_weight_sum
            if congestion_weight_sum > 0.0
            else 1.0
        )
        transfer_fragility_score = (
            transfer_fragility_sum / transfer_count if transfer_count > 0 else 0.0
        )
        selection_reasons = self._selection_reasons(
            total_wait_minutes=total_wait,
            route_reliability_score=route_reliability_score,
            transfer_count=transfer_count,
            fragile_transfer_count=fragile_transfer_count,
            congestion_proxy_ratio=congestion_proxy_ratio,
            service_quality_score=service_quality_score,
        )
        return {
            "predicted_eta_lower_minutes": max(0.0, total_lower),
            "predicted_eta_upper_minutes": max(total_lower, total_upper),
            "route_reliability_score": max(0.05, min(0.99, route_reliability_score)),
            "total_wait_minutes": max(0.0, total_wait),
            "total_in_vehicle_minutes": max(0.0, total_in_vehicle),
            "transfer_count": transfer_count,
            "fragile_transfer_count": fragile_transfer_count,
            "transfer_fragility_score": _clamp(transfer_fragility_score, 0.0, 0.99),
            "congestion_proxy_ratio": max(0.0, congestion_proxy_ratio),
            "congestion_proxy_percent": (congestion_proxy_ratio - 1.0) * 100.0,
            "service_quality_score": _clamp(service_quality_score, 0.05, 1.0),
            "selection_reasons": selection_reasons,
            "explanation_summary": selection_reasons[0],
            "cost_breakdown": cost_breakdown,
        }
