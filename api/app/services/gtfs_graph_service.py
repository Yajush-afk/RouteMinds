from __future__ import annotations

import csv
import math
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from heapq import nsmallest
from pathlib import Path

from api.app.core.config import REPO_ROOT
from api.app.core.exceptions import GTFSStaticDataException

REQUIRED_GTFS_FILES = ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt")
EARTH_RADIUS_KM = 6373.2526
SERVICE_DAY_SECONDS = 24 * 60 * 60
DELHI_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


@dataclass(frozen=True, slots=True)
class StopNode:
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float


@dataclass(frozen=True, slots=True)
class SegmentEdge:
    route_id: str
    from_stop_id: str
    to_stop_id: str
    stop_sequence: int
    normalized_stop_position: float
    distance_to_prev_stop_km: float
    scheduled_segment_minutes: float
    scheduled_departure_seconds: tuple[int, ...] = ()

    def get_next_departure_unix(self, reference_timestamp: int) -> int | None:
        if not self.scheduled_departure_seconds:
            return reference_timestamp

        service_day_start = service_day_start_unix(reference_timestamp)
        seconds_since_day_start = reference_timestamp - service_day_start
        departure_index = bisect_left(
            self.scheduled_departure_seconds,
            seconds_since_day_start,
        )
        if departure_index < len(self.scheduled_departure_seconds):
            return service_day_start + self.scheduled_departure_seconds[departure_index]
        return (
            service_day_start
            + SERVICE_DAY_SECONDS
            + self.scheduled_departure_seconds[0]
        )


@dataclass(frozen=True, slots=True)
class StaticTransitGraph:
    stops_by_id: dict[str, StopNode]
    edges: tuple[SegmentEdge, ...]
    edges_from_stop: dict[str, tuple[SegmentEdge, ...]]

    @property
    def stop_count(self) -> int:
        return len(self.stops_by_id)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_outgoing_edges(self, stop_id: str) -> tuple[SegmentEdge, ...]:
        return self.edges_from_stop.get(str(stop_id), ())


@dataclass(frozen=True, slots=True)
class TripStopEvent:
    stop_id: str
    stop_sequence: int
    arrival_seconds: int
    departure_seconds: int


def resolve_gtfs_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def parse_gtfs_time_to_seconds(value: str) -> int:
    parts = value.strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid GTFS time value: {value!r}")
    hours, minutes, seconds = (int(part) for part in parts)
    return hours * 3600 + minutes * 60 + seconds


def service_day_start_unix(reference_timestamp: int) -> int:
    local_datetime = datetime.fromtimestamp(reference_timestamp, tz=DELHI_TIMEZONE)
    return int(
        local_datetime.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    )


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def load_stops(gtfs_dir: Path) -> dict[str, StopNode]:
    stops_path = gtfs_dir / "stops.txt"
    stops_by_id: dict[str, StopNode] = {}
    with stops_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stop_id = str(row["stop_id"])
            stops_by_id[stop_id] = StopNode(
                stop_id=stop_id,
                stop_name=row.get("stop_name", stop_id),
                stop_lat=float(row["stop_lat"]),
                stop_lon=float(row["stop_lon"]),
            )
    if not stops_by_id:
        raise GTFSStaticDataException("GTFS stops.txt did not contain any stops.")
    return stops_by_id


def load_trip_routes(gtfs_dir: Path) -> dict[str, str]:
    trips_path = gtfs_dir / "trips.txt"
    trip_routes: dict[str, str] = {}
    with trips_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trip_routes[str(row["trip_id"])] = str(row["route_id"])
    if not trip_routes:
        raise GTFSStaticDataException("GTFS trips.txt did not contain any trips.")
    return trip_routes


def load_trip_stop_events(
    gtfs_dir: Path,
    *,
    stops_by_id: dict[str, StopNode],
    trip_routes: dict[str, str],
) -> dict[str, tuple[TripStopEvent, ...]]:
    stop_times_path = gtfs_dir / "stop_times.txt"
    trip_stop_events: dict[str, list[TripStopEvent]] = defaultdict(list)

    with stop_times_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trip_id = str(row["trip_id"])
            stop_id = str(row["stop_id"])

            if trip_id not in trip_routes:
                raise GTFSStaticDataException(
                    f"stop_times.txt references unknown trip_id '{trip_id}'."
                )
            if stop_id not in stops_by_id:
                raise GTFSStaticDataException(
                    f"stop_times.txt references unknown stop_id '{stop_id}'."
                )

            trip_stop_events[trip_id].append(
                TripStopEvent(
                    stop_id=stop_id,
                    stop_sequence=int(row["stop_sequence"]),
                    arrival_seconds=parse_gtfs_time_to_seconds(row["arrival_time"]),
                    departure_seconds=parse_gtfs_time_to_seconds(row["departure_time"]),
                )
            )

    if not trip_stop_events:
        raise GTFSStaticDataException(
            "GTFS stop_times.txt did not contain any trip stop sequences."
        )

    return {
        trip_id: tuple(
            sorted(
                events,
                key=lambda event: (
                    event.stop_sequence,
                    event.arrival_seconds,
                    event.departure_seconds,
                    event.stop_id,
                ),
            )
        )
        for trip_id, events in trip_stop_events.items()
    }


def _required_gtfs_paths(gtfs_dir: Path) -> None:
    missing_files = [
        file_name
        for file_name in REQUIRED_GTFS_FILES
        if not (gtfs_dir / file_name).exists()
    ]
    if missing_files:
        missing = ", ".join(missing_files)
        raise GTFSStaticDataException(
            f"Missing required GTFS static files in '{gtfs_dir}': {missing}."
        )


@lru_cache(maxsize=4)
def build_static_transit_graph(gtfs_dir: str) -> StaticTransitGraph:
    resolved_dir = resolve_gtfs_path(gtfs_dir)
    _required_gtfs_paths(resolved_dir)

    stops_by_id = load_stops(resolved_dir)
    trip_routes = load_trip_routes(resolved_dir)
    trip_stop_events = load_trip_stop_events(
        resolved_dir,
        stops_by_id=stops_by_id,
        trip_routes=trip_routes,
    )

    edge_stats: dict[tuple[str, str, str, int], dict[str, float | list[int]]] = {}

    for trip_id, trip_events in trip_stop_events.items():
        if len(trip_events) < 2:
            continue

        route_id = trip_routes[trip_id]
        max_sequence = max(event.stop_sequence for event in trip_events)
        for previous_event, current_event in zip(trip_events, trip_events[1:]):
            if current_event.stop_sequence <= previous_event.stop_sequence:
                continue

            from_stop = stops_by_id[previous_event.stop_id]
            to_stop = stops_by_id[current_event.stop_id]
            normalized_stop_position = (
                current_event.stop_sequence / max_sequence if max_sequence > 0 else 0.0
            )
            scheduled_segment_minutes = max(
                0.0,
                (current_event.arrival_seconds - previous_event.departure_seconds) / 60.0,
            )
            distance_to_prev_stop_km = haversine_km(
                from_stop.stop_lat,
                from_stop.stop_lon,
                to_stop.stop_lat,
                to_stop.stop_lon,
            )

            edge_key = (
                route_id,
                previous_event.stop_id,
                current_event.stop_id,
                current_event.stop_sequence,
            )
            stats = edge_stats.setdefault(
                edge_key,
                {
                    "count": 0.0,
                    "scheduled_segment_minutes_sum": 0.0,
                    "normalized_stop_position_sum": 0.0,
                    "distance_to_prev_stop_km_sum": 0.0,
                    "scheduled_departure_seconds": [],
                },
            )
            stats["count"] += 1.0
            stats["scheduled_segment_minutes_sum"] += scheduled_segment_minutes
            stats["normalized_stop_position_sum"] += normalized_stop_position
            stats["distance_to_prev_stop_km_sum"] += distance_to_prev_stop_km
            departure_schedule = stats["scheduled_departure_seconds"]
            assert isinstance(departure_schedule, list)
            departure_schedule.append(previous_event.departure_seconds)

    edges = []
    for (route_id, from_stop_id, to_stop_id, stop_sequence), stats in sorted(
        edge_stats.items(),
        key=lambda item: (item[0][1], item[0][0], item[0][3], item[0][2]),
    ):
        count = float(stats["count"])
        departure_schedule = stats["scheduled_departure_seconds"]
        assert isinstance(departure_schedule, list)
        edges.append(
            SegmentEdge(
                route_id=route_id,
                from_stop_id=from_stop_id,
                to_stop_id=to_stop_id,
                stop_sequence=stop_sequence,
                normalized_stop_position=float(
                    stats["normalized_stop_position_sum"]
                )
                / count,
                distance_to_prev_stop_km=float(
                    stats["distance_to_prev_stop_km_sum"]
                )
                / count,
                scheduled_segment_minutes=float(
                    stats["scheduled_segment_minutes_sum"]
                )
                / count,
                scheduled_departure_seconds=tuple(sorted(departure_schedule)),
            )
        )

    if not edges:
        raise GTFSStaticDataException(
            "GTFS graph build produced no segment edges from stop_times.txt."
        )

    edges_from_stop: dict[str, list[SegmentEdge]] = defaultdict(list)
    for edge in edges:
        edges_from_stop[edge.from_stop_id].append(edge)

    return StaticTransitGraph(
        stops_by_id=stops_by_id,
        edges=tuple(edges),
        edges_from_stop={
            stop_id: tuple(stop_edges)
            for stop_id, stop_edges in edges_from_stop.items()
        },
    )


class GTFSGraphService:
    def __init__(self, gtfs_static_dir: str | Path):
        self.gtfs_static_dir = resolve_gtfs_path(gtfs_static_dir)

    def get_graph(self) -> StaticTransitGraph:
        return build_static_transit_graph(str(self.gtfs_static_dir))

    def get_nearest_stops(
        self,
        latitude: float,
        longitude: float,
        *,
        limit: int = 5,
    ) -> list[dict[str, str | float]]:
        graph = self.get_graph()
        nearest_stops = nsmallest(
            max(1, limit),
            graph.stops_by_id.values(),
            key=lambda stop: haversine_km(
                latitude,
                longitude,
                stop.stop_lat,
                stop.stop_lon,
            ),
        )
        return [
            {
                "stop_id": stop.stop_id,
                "stop_name": stop.stop_name,
                "stop_lat": stop.stop_lat,
                "stop_lon": stop.stop_lon,
                "distance_km": haversine_km(
                    latitude,
                    longitude,
                    stop.stop_lat,
                    stop.stop_lon,
                ),
            }
            for stop in nearest_stops
        ]
