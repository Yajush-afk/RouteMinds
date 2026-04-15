from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any

from api.app.core.config import settings
from api.app.core.exceptions import RouteNotFoundException
from api.app.services.gtfs_graph_service import GTFSGraphService, SegmentEdge, StopNode
from api.app.services.prediction_service import PredictionService
from api.app.services.route_optimization_service import RouteOptimizationService
from api.training.config import resolve_repo_path

DEFAULT_OUTPUT_PATH = "artifacts/metrics/prototype_demo_scenarios.json"
MAX_SEARCH_ORIGINS = 60
MAX_DESTINATIONS_PER_ORIGIN = 40


def _segment_to_stop_payload(stop: StopNode) -> dict[str, Any]:
    return {
        "stop_id": stop.stop_id,
        "stop_name": stop.stop_name,
        "stop_lat": stop.stop_lat,
        "stop_lon": stop.stop_lon,
    }


def _build_bfs_path(
    graph_service: GTFSGraphService,
    origin_stop_id: str,
    min_depth: int,
    max_depth: int,
) -> list[SegmentEdge] | None:
    queue: deque[tuple[str, list[SegmentEdge]]] = deque([(origin_stop_id, [])])
    visited_depth: dict[str, int] = {origin_stop_id: 0}

    while queue:
        stop_id, path = queue.popleft()
        if min_depth <= len(path) <= max_depth:
            return path
        if len(path) >= max_depth:
            continue

        for edge in graph_service.get_graph().get_outgoing_edges(stop_id):
            next_depth = len(path) + 1
            previous_depth = visited_depth.get(edge.to_stop_id)
            if previous_depth is not None and previous_depth <= next_depth:
                continue
            visited_depth[edge.to_stop_id] = next_depth
            queue.append((edge.to_stop_id, [*path, edge]))

    return None


def _candidate_destinations(
    graph_service: GTFSGraphService,
    origin_stop_id: str,
    *,
    max_destinations: int,
) -> list[str]:
    destinations: list[str] = []
    queue: deque[tuple[str, int]] = deque([(origin_stop_id, 0)])
    visited: set[str] = {origin_stop_id}

    while queue and len(destinations) < max_destinations:
        stop_id, depth = queue.popleft()
        if depth > 0:
            destinations.append(stop_id)
        if depth >= 4:
            continue
        for edge in graph_service.get_graph().get_outgoing_edges(stop_id):
            if edge.to_stop_id in visited:
                continue
            visited.add(edge.to_stop_id)
            queue.append((edge.to_stop_id, depth + 1))

    return destinations


def _serialize_result(
    graph_service: GTFSGraphService,
    *,
    label: str,
    origin_stop_id: str,
    destination_stop_id: str,
    result,
) -> dict[str, Any]:
    graph = graph_service.get_graph()
    origin_stop = graph.stops_by_id[origin_stop_id]
    destination_stop = graph.stops_by_id[destination_stop_id]
    origin_resolution = graph_service.get_nearest_stops(
        origin_stop.stop_lat,
        origin_stop.stop_lon,
        limit=1,
    )
    destination_resolution = graph_service.get_nearest_stops(
        destination_stop.stop_lat,
        destination_stop.stop_lon,
        limit=1,
    )
    return {
        "label": label,
        "origin_stop": _segment_to_stop_payload(origin_stop),
        "destination_stop": _segment_to_stop_payload(destination_stop),
        "stop_resolution": {
            "origin_nearest_stop_id": origin_resolution[0]["stop_id"] if origin_resolution else None,
            "destination_nearest_stop_id": destination_resolution[0]["stop_id"] if destination_resolution else None,
            "strategy": "nearest_stop",
        },
        "route_summary": {
            "total_predicted_eta_minutes": result.total_predicted_eta_minutes,
            "predicted_eta_lower_minutes": result.predicted_eta_lower_minutes,
            "predicted_eta_upper_minutes": result.predicted_eta_upper_minutes,
            "route_reliability_score": result.route_reliability_score,
            "generalized_cost_minutes": result.generalized_cost_minutes,
            "total_wait_minutes": result.total_wait_minutes,
            "transfer_count": result.transfer_count,
            "fragile_transfer_count": result.fragile_transfer_count,
            "congestion_proxy_percent": result.congestion_proxy_percent,
            "service_quality_score": result.service_quality_score,
            "selection_reasons": result.selection_reasons,
            "explanation_summary": result.explanation_summary,
        },
        "ordered_stop_coordinates": [
            {"stop_id": stop["stop_id"], "lat": stop["stop_lat"], "lon": stop["stop_lon"]}
            for stop in result.stops
        ],
    }


def validate_prototype_demo_scenarios(output_path: str | Path = DEFAULT_OUTPUT_PATH) -> dict[str, Any]:
    graph_service = GTFSGraphService(settings.GTFS_STATIC_DIR)
    prediction_service = PredictionService(settings.MODEL_PATH, settings.SCHEMA_PATH)
    route_service = RouteOptimizationService(graph_service, prediction_service)
    graph = graph_service.get_graph()
    query_timestamp_unix = int(time.time())

    direct_edge = next(iter(graph.edges))
    direct_result = route_service.optimize_route(
        direct_edge.from_stop_id,
        direct_edge.to_stop_id,
        query_timestamp_unix,
    )

    multi_path_origin = direct_edge.from_stop_id
    multi_path = _build_bfs_path(graph_service, multi_path_origin, min_depth=3, max_depth=5)
    if multi_path is None:
        raise RuntimeError("Unable to derive a multi-stop scenario from the GTFS graph.")
    multi_result = route_service.optimize_route(
        multi_path[0].from_stop_id,
        multi_path[-1].to_stop_id,
        query_timestamp_unix,
    )

    transfer_result = None
    transfer_origin_stop_id = None
    transfer_destination_stop_id = None
    candidate_origins = list(graph.edges_from_stop.keys())[:MAX_SEARCH_ORIGINS]
    for origin_stop_id in candidate_origins:
        for destination_stop_id in _candidate_destinations(
            graph_service,
            origin_stop_id,
            max_destinations=MAX_DESTINATIONS_PER_ORIGIN,
        ):
            try:
                candidate_result = route_service.optimize_route(
                    origin_stop_id,
                    destination_stop_id,
                    query_timestamp_unix,
                )
            except RouteNotFoundException:
                continue
            if candidate_result.transfer_count > 0:
                transfer_result = candidate_result
                transfer_origin_stop_id = origin_stop_id
                transfer_destination_stop_id = destination_stop_id
                break
        if transfer_result is not None:
            break

    scenarios = [
        _serialize_result(
            graph_service,
            label="direct_route",
            origin_stop_id=direct_edge.from_stop_id,
            destination_stop_id=direct_edge.to_stop_id,
            result=direct_result,
        ),
        _serialize_result(
            graph_service,
            label="multi_stop_route",
            origin_stop_id=multi_path[0].from_stop_id,
            destination_stop_id=multi_path[-1].to_stop_id,
            result=multi_result,
        ),
    ]

    if transfer_result is not None and transfer_origin_stop_id and transfer_destination_stop_id:
        scenarios.append(
            _serialize_result(
                graph_service,
                label="transfer_route",
                origin_stop_id=transfer_origin_stop_id,
                destination_stop_id=transfer_destination_stop_id,
                result=transfer_result,
            )
        )

    payload = {
        "query_timestamp_unix": query_timestamp_unix,
        "route_drawing_contract": "Frontend should draw prototype route polylines using ordered stop coordinates from the route response.",
        "stop_resolution_contract": "Frontend should resolve each selected place through /stops/nearby and use the nearest returned stop for the prototype.",
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }
    resolved_output_path = resolve_repo_path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    payload = validate_prototype_demo_scenarios()
    print("Prototype demo scenario validation finished.")
    print(f"Scenarios validated: {payload['scenario_count']}")
    print(f"Output: {resolve_repo_path(DEFAULT_OUTPUT_PATH)}")


if __name__ == "__main__":
    main()
