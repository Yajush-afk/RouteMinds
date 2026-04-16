from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass
from itertools import count

from api.app.core.exceptions import RouteNotFoundException, StopNotFoundException
from api.app.services.gtfs_graph_service import (
    GTFSGraphService,
    SegmentEdge,
    StaticTransitGraph,
    haversine_km,
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
MAX_CANDIDATE_PATHS = 6
MAX_LABELS_PER_STATE = 2
MAX_ROUTE_STEPS = 192
MAX_EXPANDED_LABELS = 50_000
CANDIDATE_COST_MARGIN_MINUTES = 12.0
CANDIDATE_COST_RATIO = 1.5
STATE_COST_DUPLICATE_EPSILON = 0.05


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
    route_path_coordinates: list[dict[str, str | float]]
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


@dataclass(frozen=True, slots=True)
class CandidateStep:
    from_state: RouteState
    to_state: RouteState
    edge: SegmentEdge


@dataclass(frozen=True, slots=True)
class SearchLabel:
    label_id: int
    state: RouteState
    generalized_cost: float
    eta_minutes: float
    arrival_timestamp: int
    step_count: int
    predecessor_label_id: int | None
    edge: SegmentEdge | None


@dataclass(frozen=True, slots=True)
class ScoredCandidate:
    route_steps: list[RouteStep]
    edge_prediction_cache: dict[tuple[SegmentEdge, int], dict[str, float]]
    total_predicted_eta_minutes: float
    generalized_cost_minutes: float


@dataclass(frozen=True, slots=True)
class StopVariant:
    stop_id: str
    distance_km: float


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
                route_path_coordinates=[
                    {
                        "stop_id": stop.stop_id,
                        "lat": stop.stop_lat,
                        "lon": stop.stop_lon,
                    }
                ],
                alternatives=[],
            )

        best_candidate = self._find_best_route_candidate(
            graph,
            origin_stop_key,
            destination_stop_key,
            query_timestamp_unix,
        )
        if best_candidate is None or not best_candidate.route_steps:
            raise RouteNotFoundException(origin_stop_key, destination_stop_key)

        route_origin_stop_id = best_candidate.route_steps[0].from_state.stop_id
        stops = self._build_stop_path(graph, route_origin_stop_id, best_candidate.route_steps)
        segments = self._build_segment_predictions(
            best_candidate.route_steps,
            best_candidate.edge_prediction_cache,
        )
        route_summary = self._build_route_summary(segments)

        return RouteOptimizationResult(
            stops=stops,
            segments=segments,
            total_predicted_eta_minutes=best_candidate.total_predicted_eta_minutes,
            predicted_eta_lower_minutes=route_summary["predicted_eta_lower_minutes"],
            predicted_eta_upper_minutes=route_summary["predicted_eta_upper_minutes"],
            route_reliability_score=route_summary["route_reliability_score"],
            generalized_cost_minutes=best_candidate.generalized_cost_minutes,
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
            route_path_coordinates=self._build_route_path_coordinates(stops),
            alternatives=[],
        )

    def _find_best_route_candidate(
        self,
        graph: StaticTransitGraph,
        origin_stop_id: str,
        destination_stop_id: str,
        query_timestamp_unix: int,
    ) -> ScoredCandidate | None:
        exact_candidate = self._score_best_pair_candidate(
            graph,
            [(StopVariant(origin_stop_id, 0.0), StopVariant(destination_stop_id, 0.0))],
            query_timestamp_unix=query_timestamp_unix,
        )
        if exact_candidate is not None:
            return exact_candidate

        origin_variants = self._resolve_stop_variants(graph, origin_stop_id)
        destination_variants = self._resolve_stop_variants(graph, destination_stop_id)
        fallback_phases = [
            [
                (origin_variant, destination_variants[0])
                for origin_variant in origin_variants[1:]
            ],
            [
                (origin_variants[0], destination_variant)
                for destination_variant in destination_variants[1:]
            ],
            [
                (origin_variant, destination_variant)
                for origin_variant in origin_variants[1:]
                for destination_variant in destination_variants[1:]
            ],
        ]
        for stop_pairs in fallback_phases:
            scored_candidate = self._score_best_pair_candidate(
                graph,
                stop_pairs,
                query_timestamp_unix=query_timestamp_unix,
            )
            if scored_candidate is not None:
                return scored_candidate

        return None

    def _score_best_pair_candidate(
        self,
        graph: StaticTransitGraph,
        stop_pairs: list[tuple[StopVariant, StopVariant]],
        *,
        query_timestamp_unix: int,
    ) -> ScoredCandidate | None:
        best_candidate: ScoredCandidate | None = None
        for origin_variant, destination_variant in stop_pairs:
            if not self._stop_graph_reachable(
                graph,
                origin_variant.stop_id,
                destination_variant.stop_id,
            ):
                continue
            candidate_paths = self._collect_candidate_paths(
                graph,
                origin_variant.stop_id,
                destination_variant.stop_id,
                query_timestamp_unix,
            )
            if not candidate_paths:
                continue

            access_penalty_minutes = (origin_variant.distance_km + destination_variant.distance_km) * 12.0
            for candidate_path in candidate_paths:
                scored_candidate = self._score_candidate_path(
                    candidate_path,
                    query_timestamp_unix=query_timestamp_unix,
                )
                scored_candidate = ScoredCandidate(
                    route_steps=scored_candidate.route_steps,
                    edge_prediction_cache=scored_candidate.edge_prediction_cache,
                    total_predicted_eta_minutes=(
                        scored_candidate.total_predicted_eta_minutes
                    ),
                    generalized_cost_minutes=(
                        scored_candidate.generalized_cost_minutes + access_penalty_minutes
                    ),
                )
                if best_candidate is None:
                    best_candidate = scored_candidate
                    continue

                current_rank = (
                    scored_candidate.generalized_cost_minutes,
                    scored_candidate.total_predicted_eta_minutes,
                    len(scored_candidate.route_steps),
                )
                best_rank = (
                    best_candidate.generalized_cost_minutes,
                    best_candidate.total_predicted_eta_minutes,
                    len(best_candidate.route_steps),
                )
                if current_rank < best_rank:
                    best_candidate = scored_candidate

        return best_candidate

    def _stop_graph_reachable(
        self,
        graph: StaticTransitGraph,
        origin_stop_id: str,
        destination_stop_id: str,
    ) -> bool:
        if origin_stop_id == destination_stop_id:
            return True

        visited = {origin_stop_id}
        queue = deque([origin_stop_id])
        while queue:
            current_stop_id = queue.popleft()
            for edge in graph.get_outgoing_edges(current_stop_id):
                if edge.to_stop_id == destination_stop_id:
                    return True
                if edge.to_stop_id in visited:
                    continue
                visited.add(edge.to_stop_id)
                queue.append(edge.to_stop_id)
        return False

    def _collect_candidate_paths(
        self,
        graph: StaticTransitGraph,
        origin_stop_id: str,
        destination_stop_id: str,
        query_timestamp_unix: int,
    ) -> list[list[CandidateStep]]:
        origin_state = RouteState(stop_id=origin_stop_id, active_route_id=None)
        label_sequence = count()
        priority_sequence = count()
        origin_label = SearchLabel(
            label_id=next(label_sequence),
            state=origin_state,
            generalized_cost=0.0,
            eta_minutes=0.0,
            arrival_timestamp=query_timestamp_unix,
            step_count=0,
            predecessor_label_id=None,
            edge=None,
        )
        labels_by_id: dict[int, SearchLabel] = {origin_label.label_id: origin_label}
        accepted_costs_by_state: dict[RouteState, list[float]] = {origin_state: [0.0]}
        heap: list[tuple[float, int, int]] = [
            (0.0, next(priority_sequence), origin_label.label_id)
        ]
        destination_label_ids: list[int] = []
        best_destination_cost: float | None = None
        expanded_labels = 0

        while heap:
            current_distance, _, label_id = heapq.heappop(heap)
            current_label = labels_by_id[label_id]
            if not self._is_active_label(
                accepted_costs_by_state.get(current_label.state, []),
                current_label.generalized_cost,
            ):
                continue
            if current_distance > current_label.generalized_cost + STATE_COST_DUPLICATE_EPSILON:
                continue

            if (
                best_destination_cost is not None
                and destination_label_ids
                and len(destination_label_ids) >= MAX_CANDIDATE_PATHS
            ):
                exploration_limit = max(
                    best_destination_cost + CANDIDATE_COST_MARGIN_MINUTES,
                    best_destination_cost * CANDIDATE_COST_RATIO,
                )
                if current_distance > exploration_limit:
                    break

            expanded_labels += 1
            if expanded_labels > MAX_EXPANDED_LABELS:
                break

            if current_label.state.stop_id == destination_stop_id:
                destination_label_ids.append(label_id)
                if (
                    best_destination_cost is None
                    or current_label.generalized_cost < best_destination_cost
                ):
                    best_destination_cost = current_label.generalized_cost
                continue

            if current_label.step_count >= MAX_ROUTE_STEPS:
                continue

            outgoing_edges = graph.get_outgoing_edges(current_label.state.stop_id)
            if not outgoing_edges:
                continue

            edge_departure_timestamps = self._resolve_edge_departure_timestamps(
                outgoing_edges,
                current_state=current_label.state,
                current_arrival_timestamp=current_label.arrival_timestamp,
            )
            if not edge_departure_timestamps:
                continue

            for edge, departure_timestamp in edge_departure_timestamps.items():
                scheduled_wait_minutes_before_boarding = max(
                    0.0,
                    (departure_timestamp - current_label.arrival_timestamp) / 60.0,
                )
                edge_weight = max(edge.scheduled_segment_minutes, MIN_EDGE_WEIGHT_MINUTES)
                transfer_penalty_cost = self._transfer_penalty_cost(
                    current_route_id=current_label.state.active_route_id,
                    next_route_id=edge.route_id,
                )
                detour_penalty_cost = self._detour_penalty_minutes(edge=edge)
                candidate_distance = (
                    current_label.generalized_cost
                    + scheduled_wait_minutes_before_boarding
                    + edge_weight
                    + transfer_penalty_cost
                    + detour_penalty_cost
                )
                candidate_eta = (
                    current_label.eta_minutes
                    + scheduled_wait_minutes_before_boarding
                    + edge_weight
                )
                next_state = RouteState(
                    stop_id=edge.to_stop_id,
                    active_route_id=edge.route_id,
                )
                existing_costs = accepted_costs_by_state.get(next_state, [])
                if not self._should_accept_label(existing_costs, candidate_distance):
                    continue

                next_label = SearchLabel(
                    label_id=next(label_sequence),
                    state=next_state,
                    generalized_cost=candidate_distance,
                    eta_minutes=candidate_eta,
                    arrival_timestamp=departure_timestamp + int(round(edge_weight * 60.0)),
                    step_count=current_label.step_count + 1,
                    predecessor_label_id=current_label.label_id,
                    edge=edge,
                )
                labels_by_id[next_label.label_id] = next_label
                accepted_costs_by_state[next_state] = self._record_label_cost(
                    existing_costs,
                    candidate_distance,
                )
                heapq.heappush(
                    heap,
                    (
                        next_label.generalized_cost,
                        next(priority_sequence),
                        next_label.label_id,
                    ),
                )

        if not destination_label_ids:
            return []

        candidate_paths: list[list[CandidateStep]] = []
        seen_paths: set[tuple[tuple[str, str, str, int], ...]] = set()
        ranked_destination_labels = sorted(
            destination_label_ids,
            key=lambda label_id: labels_by_id[label_id].generalized_cost,
        )
        for destination_label_id in ranked_destination_labels:
            candidate_path = self._reconstruct_candidate_path(
                labels_by_id,
                destination_label_id,
            )
            if not candidate_path:
                continue
            candidate_key = tuple(
                (
                    step.edge.route_id,
                    step.edge.from_stop_id,
                    step.edge.to_stop_id,
                    step.edge.stop_sequence,
                )
                for step in candidate_path
            )
            if candidate_key in seen_paths:
                continue
            seen_paths.add(candidate_key)
            candidate_paths.append(candidate_path)
            if len(candidate_paths) >= MAX_CANDIDATE_PATHS:
                break

        return candidate_paths

    def _score_candidate_path(
        self,
        candidate_path: list[CandidateStep],
        *,
        query_timestamp_unix: int,
    ) -> ScoredCandidate:
        total_predicted_eta_minutes = 0.0
        generalized_cost_minutes = 0.0
        route_steps: list[RouteStep] = []
        edge_prediction_cache: dict[tuple[SegmentEdge, int], dict[str, float]] = {}
        initial_timeline = self._materialize_candidate_timeline(
            candidate_path,
            query_timestamp_unix=query_timestamp_unix,
        )
        initial_predictions = self._predict_timeline_segments(initial_timeline)
        predicted_travel_minutes_by_index = {
            index: max(
                float(prediction["predicted_actual_segment_minutes"]),
                MIN_EDGE_WEIGHT_MINUTES,
            )
            for index, prediction in enumerate(initial_predictions)
        }
        final_timeline = self._materialize_candidate_timeline(
            candidate_path,
            query_timestamp_unix=query_timestamp_unix,
            predicted_travel_minutes_by_index=predicted_travel_minutes_by_index,
        )
        final_predictions = self._predict_timeline_segments(final_timeline)

        for timeline_item, prediction in zip(final_timeline, final_predictions, strict=True):
            candidate_step = timeline_item["candidate_step"]
            edge = candidate_step.edge
            departure_timestamp = int(timeline_item["departure_timestamp"])
            current_arrival_timestamp = int(timeline_item["arrival_timestamp"])
            scheduled_wait_minutes_before_boarding = float(
                timeline_item["scheduled_wait_minutes_before_boarding"]
            )
            segment_record = timeline_item["segment_record"]

            enriched_prediction = {
                **segment_record,
                **prediction,
            }
            edge_prediction_cache[(edge, departure_timestamp)] = enriched_prediction
            edge_weight = max(
                float(enriched_prediction["predicted_actual_segment_minutes"]),
                MIN_EDGE_WEIGHT_MINUTES,
            )
            wait_minutes_before_boarding, boarding_feasibility_score = (
                self._estimate_wait_and_boarding(
                    edge=edge,
                    current_state=candidate_step.from_state,
                    current_arrival_timestamp=current_arrival_timestamp,
                    scheduled_wait_minutes=scheduled_wait_minutes_before_boarding,
                )
            )
            reliability_penalty_minutes = self._reliability_penalty_minutes(
                prediction=enriched_prediction,
                boarding_feasibility_score=boarding_feasibility_score,
            )
            transfer_assessment = self._transfer_assessment(
                edge=edge,
                current_state=candidate_step.from_state,
                prediction=enriched_prediction,
                scheduled_wait_minutes=scheduled_wait_minutes_before_boarding,
                boarding_feasibility_score=boarding_feasibility_score,
            )
            cost_breakdown = self._generalized_cost_breakdown(
                edge=edge,
                current_state=candidate_step.from_state,
                prediction=enriched_prediction,
                travel_time_minutes=edge_weight,
                wait_minutes=wait_minutes_before_boarding,
                reliability_penalty_minutes=reliability_penalty_minutes,
                boarding_feasibility_score=boarding_feasibility_score,
                transfer_assessment=transfer_assessment,
            )
            route_steps.append(
                RouteStep(
                    from_state=candidate_step.from_state,
                    to_state=candidate_step.to_state,
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
            )
            total_predicted_eta_minutes += wait_minutes_before_boarding + edge_weight
            generalized_cost_minutes += cost_breakdown.generalized_cost

        return ScoredCandidate(
            route_steps=route_steps,
            edge_prediction_cache=edge_prediction_cache,
            total_predicted_eta_minutes=total_predicted_eta_minutes,
            generalized_cost_minutes=generalized_cost_minutes,
        )

    def _materialize_candidate_timeline(
        self,
        candidate_path: list[CandidateStep],
        *,
        query_timestamp_unix: int,
        predicted_travel_minutes_by_index: dict[int, float] | None = None,
    ) -> list[dict[str, object]]:
        timeline: list[dict[str, object]] = []
        current_arrival_timestamp = query_timestamp_unix

        for index, candidate_step in enumerate(candidate_path):
            edge = candidate_step.edge
            departure_timestamp = self._resolve_departure_timestamp_for_edge(
                edge=edge,
                current_state=candidate_step.from_state,
                current_arrival_timestamp=current_arrival_timestamp,
            )
            if departure_timestamp is None:
                raise RouteNotFoundException(
                    candidate_step.from_state.stop_id,
                    candidate_step.to_state.stop_id,
                )

            timeline.append(
                {
                    "candidate_step": candidate_step,
                    "arrival_timestamp": current_arrival_timestamp,
                    "departure_timestamp": departure_timestamp,
                    "scheduled_wait_minutes_before_boarding": max(
                        0.0,
                        (departure_timestamp - current_arrival_timestamp) / 60.0,
                    ),
                    "segment_record": self._build_segment_record(edge, departure_timestamp),
                }
            )

            travel_minutes = (
                predicted_travel_minutes_by_index.get(index, edge.scheduled_segment_minutes)
                if predicted_travel_minutes_by_index
                else edge.scheduled_segment_minutes
            )
            current_arrival_timestamp = departure_timestamp + int(
                round(max(travel_minutes, MIN_EDGE_WEIGHT_MINUTES) * 60.0)
            )

        return timeline

    def _prediction_service_supports_segment_record(
        self,
        segment_record: dict[str, str | int | float],
    ) -> bool:
        supports_segment_record = getattr(
            self.prediction_service,
            "supports_segment_record",
            None,
        )
        if not callable(supports_segment_record):
            return True
        return bool(supports_segment_record(segment_record))

    def _predict_timeline_segments(
        self,
        timeline: list[dict[str, object]],
    ) -> list[dict[str, float | str | bool]]:
        predictions: list[dict[str, float | str | bool] | None] = [None] * len(timeline)
        supported_indices: list[int] = []
        supported_records: list[dict[str, str | int | float]] = []

        for index, timeline_item in enumerate(timeline):
            segment_record = timeline_item["segment_record"]
            if not isinstance(segment_record, dict):
                raise TypeError("Candidate timeline item is missing a segment record.")
            if self._prediction_service_supports_segment_record(segment_record):
                supported_indices.append(index)
                supported_records.append(segment_record)
                continue

            candidate_step = timeline_item["candidate_step"]
            departure_timestamp = int(timeline_item["departure_timestamp"])
            if not isinstance(candidate_step, CandidateStep):
                raise TypeError("Candidate timeline item is missing a candidate step.")
            predictions[index] = self._build_coarse_prediction(
                edge=candidate_step.edge,
                departure_timestamp=departure_timestamp,
                segment_record=segment_record,
            )

        if supported_records:
            supported_predictions = self.prediction_service.predict_segments(supported_records)
            for index, prediction in zip(
                supported_indices,
                supported_predictions,
                strict=True,
            ):
                predictions[index] = prediction

        return [
            prediction
            for prediction in predictions
            if prediction is not None
        ]

    def _reconstruct_candidate_path(
        self,
        labels_by_id: dict[int, SearchLabel],
        destination_label_id: int,
    ) -> list[CandidateStep]:
        path: list[CandidateStep] = []
        current_label = labels_by_id[destination_label_id]

        while current_label.predecessor_label_id is not None and current_label.edge is not None:
            previous_label = labels_by_id[current_label.predecessor_label_id]
            path.append(
                CandidateStep(
                    from_state=previous_label.state,
                    to_state=current_label.state,
                    edge=current_label.edge,
                )
            )
            current_label = previous_label

        path.reverse()
        return path

    def _resolve_edge_departure_timestamps(
        self,
        outgoing_edges: tuple[SegmentEdge, ...],
        *,
        current_state: RouteState,
        current_arrival_timestamp: int,
    ) -> dict[SegmentEdge, int]:
        departure_timestamps: dict[SegmentEdge, int] = {}
        for edge in outgoing_edges:
            departure_timestamp = self._resolve_departure_timestamp_for_edge(
                edge=edge,
                current_state=current_state,
                current_arrival_timestamp=current_arrival_timestamp,
            )
            if departure_timestamp is None:
                continue
            departure_timestamps[edge] = departure_timestamp
        return departure_timestamps

    def _resolve_departure_timestamp_for_edge(
        self,
        *,
        edge: SegmentEdge,
        current_state: RouteState,
        current_arrival_timestamp: int,
    ) -> int | None:
        if (
            current_state.active_route_id is not None
            and current_state.active_route_id == edge.route_id
        ):
            return current_arrival_timestamp
        transfer_buffer_minutes = self._transfer_buffer_minutes(
            current_route_id=current_state.active_route_id,
            next_route_id=edge.route_id,
        )
        earliest_board_timestamp = current_arrival_timestamp + int(
            round(transfer_buffer_minutes * 60.0)
        )
        return edge.get_next_departure_unix(earliest_board_timestamp)

    def _should_accept_label(
        self,
        existing_costs: list[float],
        candidate_distance: float,
    ) -> bool:
        if any(
            abs(existing_cost - candidate_distance) <= STATE_COST_DUPLICATE_EPSILON
            for existing_cost in existing_costs
        ):
            return False
        if len(existing_costs) < MAX_LABELS_PER_STATE:
            return True
        return candidate_distance + STATE_COST_DUPLICATE_EPSILON < max(existing_costs)

    def _record_label_cost(
        self,
        existing_costs: list[float],
        candidate_distance: float,
    ) -> list[float]:
        recorded_costs = [*existing_costs, candidate_distance]
        recorded_costs.sort()
        return recorded_costs[:MAX_LABELS_PER_STATE]

    def _is_active_label(
        self,
        active_costs: list[float],
        label_cost: float,
    ) -> bool:
        return any(
            abs(active_cost - label_cost) <= STATE_COST_DUPLICATE_EPSILON
            for active_cost in active_costs
        )

    def _build_coarse_prediction(
        self,
        *,
        edge: SegmentEdge,
        departure_timestamp: int,
        segment_record: dict[str, str | int | float] | None = None,
    ) -> dict[str, float | str | bool]:
        segment_record = segment_record or self._build_segment_record(edge, departure_timestamp)
        scheduled_segment_minutes = max(
            MIN_EDGE_WEIGHT_MINUTES,
            float(segment_record["scheduled_segment_minutes"]),
        )
        segment_slowdown_index = max(
            1.0,
            float(segment_record.get("segment_slowdown_index", 1.0)),
        )
        corridor_slowdown_score_live = max(
            1.0,
            float(segment_record.get("corridor_slowdown_score_live", 1.0)),
        )
        route_delay_minutes_live = max(
            0.0,
            float(segment_record.get("route_delay_minutes_live", 0.0)),
        )
        headway_irregularity_score_live = max(
            0.0,
            float(segment_record.get("headway_irregularity_score_live", 0.0)),
        )
        bunching_indicator = max(
            0.0,
            float(segment_record.get("bunching_indicator", 0.0)),
        )
        persistent_unreliability_penalty = max(
            0.0,
            float(segment_record.get("persistent_unreliability_penalty", 0.0)),
        )
        corridor_instability_score_live = _clamp(
            float(segment_record.get("corridor_instability_score_live", 0.0)),
            0.0,
            1.0,
        )
        service_quality_score = _clamp(
            float(segment_record.get("service_quality_score", 1.0)),
            0.05,
            1.0,
        )

        slowdown_multiplier = max(
            1.0,
            segment_slowdown_index,
            1.0 + max(0.0, corridor_slowdown_score_live - 1.0) * 0.85,
        )
        predicted_actual_segment_minutes = max(
            MIN_EDGE_WEIGHT_MINUTES,
            (scheduled_segment_minutes * slowdown_multiplier)
            + min(4.0, route_delay_minutes_live / 6.0)
            + min(1.5, headway_irregularity_score_live * 0.9)
            + min(1.0, bunching_indicator * 0.75),
        )
        segment_uncertainty = _clamp(
            0.6
            + min(
                1.8,
                abs(predicted_actual_segment_minutes - scheduled_segment_minutes) * 0.3,
            )
            + min(1.0, corridor_instability_score_live * 1.2)
            + min(0.8, headway_irregularity_score_live * 0.8)
            + min(0.6, bunching_indicator * 0.6)
            + min(0.6, persistent_unreliability_penalty * 0.4),
            0.5,
            8.0,
        )
        reliability_penalty = min(0.35, (slowdown_multiplier - 1.0) * 0.18)
        reliability_penalty += min(0.2, route_delay_minutes_live / 40.0)
        reliability_penalty += min(0.15, headway_irregularity_score_live * 0.15)
        reliability_penalty += min(0.1, bunching_indicator * 0.1)
        segment_reliability_score = _clamp(
            service_quality_score - reliability_penalty,
            0.05,
            0.99,
        )
        congestion_proxy_ratio = (
            predicted_actual_segment_minutes / max(0.1, scheduled_segment_minutes)
        )

        return {
            "predicted_actual_segment_minutes": predicted_actual_segment_minutes,
            "predicted_segment_delay_minutes": (
                predicted_actual_segment_minutes - scheduled_segment_minutes
            ),
            "segment_uncertainty": segment_uncertainty,
            "segment_reliability_score": segment_reliability_score,
            "congestion_proxy_ratio": congestion_proxy_ratio,
            "congestion_proxy_percent": (congestion_proxy_ratio - 1.0) * 100.0,
            "predicted_eta_lower_minutes": max(
                MIN_EDGE_WEIGHT_MINUTES,
                predicted_actual_segment_minutes - segment_uncertainty,
            ),
            "predicted_eta_upper_minutes": (
                predicted_actual_segment_minutes + segment_uncertainty
            ),
            "prediction_source": "scheduled_fallback",
            "model_supported": False,
        }

    def _resolve_stop_variants(
        self,
        graph: StaticTransitGraph,
        stop_id: str,
    ) -> list[StopVariant]:
        stop = graph.stops_by_id[stop_id]
        variants = [StopVariant(stop_id=stop_id, distance_km=0.0)]
        seen_stop_ids = {stop_id}
        for match in self.graph_service.search_stops(stop.stop_name, limit=3):
            candidate_stop_id = str(match["stop_id"])
            if candidate_stop_id in seen_stop_ids:
                continue
            candidate_stop = graph.stops_by_id.get(candidate_stop_id)
            if candidate_stop is None:
                continue
            seen_stop_ids.add(candidate_stop_id)
            variants.append(
                StopVariant(
                    stop_id=candidate_stop_id,
                    distance_km=haversine_km(
                        stop.stop_lat,
                        stop.stop_lon,
                        candidate_stop.stop_lat,
                        candidate_stop.stop_lon,
                    ),
                )
            )
        return variants

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
                "prediction_source": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("prediction_source", "ml"),
                "model_supported": edge_prediction_cache[
                    (step.edge, step.scheduled_departure_unix)
                ].get("model_supported", True),
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

    def _build_route_path_coordinates(
        self,
        stops: list[dict[str, str | float]],
    ) -> list[dict[str, str | float]]:
        return [
            {
                "stop_id": str(stop["stop_id"]),
                "lat": float(stop["stop_lat"]),
                "lon": float(stop["stop_lon"]),
            }
            for stop in stops
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
