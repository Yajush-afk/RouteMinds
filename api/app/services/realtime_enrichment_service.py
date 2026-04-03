from __future__ import annotations

import csv
import json
import math
import time
from collections import defaultdict, deque
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from api.app.core.config import REPO_ROOT, settings
from api.app.core.exceptions import GTFSRealtimeException, GTFSStaticDataException
from api.app.services.gtfs_graph_service import resolve_gtfs_path

DELHI_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


@dataclass(frozen=True, slots=True)
class VehiclePositionSnapshot:
    vehicle_id: str
    trip_id: str
    route_id: str
    start_time: str
    start_date: str
    latitude: float
    longitude: float
    speed_mps: float
    gps_timestamp: int
    snapshot_time: int


@dataclass(frozen=True, slots=True)
class TripStopEvent:
    stop_id: str
    stop_lat: float
    stop_lon: float
    stop_sequence: int
    arrival_seconds: int
    departure_seconds: int
    route_id: str


@dataclass(frozen=True, slots=True)
class SegmentLiveContext:
    route_id: str
    from_stop_id: str
    to_stop_id: str
    prev_segment_delay: float
    rolling_segment_delay_3: float
    last_update_timestamp: int
    vehicle_id: str
    trip_id: str


@dataclass(frozen=True, slots=True)
class SegmentObservation:
    route_id: str
    from_stop_id: str
    to_stop_id: str
    delay_minutes: float
    observation_timestamp: int


def resolve_rt_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def parse_gtfs_time_to_seconds(value: str) -> int:
    hours, minutes, seconds = (int(part) for part in value.strip().split(":"))
    return hours * 3600 + minutes * 60 + seconds


def parse_service_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d").replace(tzinfo=DELHI_TIMEZONE)


def scheduled_unix_from_service_date(start_date: str, seconds_from_midnight: int) -> int:
    service_day = parse_service_date(start_date)
    return int(service_day.timestamp()) + seconds_from_midnight


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6373.2526
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
    return earth_radius_km * c


def load_trip_stop_events(gtfs_static_dir: str | Path) -> dict[str, tuple[TripStopEvent, ...]]:
    gtfs_dir = resolve_gtfs_path(gtfs_static_dir)
    stops_path = gtfs_dir / "stops.txt"
    trips_path = gtfs_dir / "trips.txt"
    stop_times_path = gtfs_dir / "stop_times.txt"

    for required_path in (stops_path, trips_path, stop_times_path):
        if not required_path.exists():
            raise GTFSStaticDataException(
                f"Missing required GTFS static file '{required_path.name}' in '{gtfs_dir}'."
            )

    stops_by_id: dict[str, tuple[float, float]] = {}
    with stops_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stops_by_id[str(row["stop_id"])] = (
                float(row["stop_lat"]),
                float(row["stop_lon"]),
            )

    trip_routes: dict[str, str] = {}
    with trips_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trip_routes[str(row["trip_id"])] = str(row["route_id"])

    trip_stop_events: dict[str, list[TripStopEvent]] = defaultdict(list)
    with stop_times_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trip_id = str(row["trip_id"])
            stop_id = str(row["stop_id"])
            if stop_id not in stops_by_id or trip_id not in trip_routes:
                continue
            stop_lat, stop_lon = stops_by_id[stop_id]
            trip_stop_events[trip_id].append(
                TripStopEvent(
                    stop_id=stop_id,
                    stop_lat=stop_lat,
                    stop_lon=stop_lon,
                    stop_sequence=int(row["stop_sequence"]),
                    arrival_seconds=parse_gtfs_time_to_seconds(row["arrival_time"]),
                    departure_seconds=parse_gtfs_time_to_seconds(row["departure_time"]),
                    route_id=trip_routes[trip_id],
                )
            )

    return {
        trip_id: tuple(sorted(events, key=lambda event: event.stop_sequence))
        for trip_id, events in trip_stop_events.items()
    }


class GTFSRealtimeIngestionService:
    def __init__(
        self,
        vehicle_positions_url: str,
        api_key: str,
        snapshot_path: str | Path | None = None,
        timeout_seconds: float = 15.0,
    ):
        self.vehicle_positions_url = vehicle_positions_url
        self.api_key = api_key
        self.snapshot_path = (
            resolve_rt_path(snapshot_path) if snapshot_path else None
        )
        self.timeout_seconds = timeout_seconds

    def fetch_vehicle_positions(self) -> list[VehiclePositionSnapshot]:
        if not self.vehicle_positions_url:
            raise GTFSRealtimeException(
                "GTFS real-time vehicle positions URL is not configured."
            )
        if not self.api_key:
            raise GTFSRealtimeException("GTFS real-time API key is not configured.")

        headers = {"Authorization": self.api_key, "x-api-key": self.api_key}
        try:
            response = httpx.get(
                self.vehicle_positions_url,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GTFSRealtimeException(
                f"Unable to fetch GTFS real-time vehicle positions: {exc}"
            ) from exc

        snapshots = self._normalize_response(response.json())
        if self.snapshot_path:
            self._persist_snapshots(snapshots)
        return snapshots

    def _normalize_response(self, payload) -> list[VehiclePositionSnapshot]:
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            for key in ("data", "records", "results", "vehicles"):
                value = payload.get(key)
                if isinstance(value, list):
                    records = value
                    break
            else:
                raise GTFSRealtimeException(
                    "GTFS real-time payload does not contain a list of records."
                )
        else:
            raise GTFSRealtimeException("Unsupported GTFS real-time payload format.")

        snapshots = []
        for record in records:
            snapshots.append(
                VehiclePositionSnapshot(
                    vehicle_id=str(record["vehicle_id"]),
                    trip_id=str(record["trip_id"]),
                    route_id=str(record["route_id"]),
                    start_time=str(record.get("start_time", "")),
                    start_date=str(record["start_date"]),
                    latitude=float(record["latitude"]),
                    longitude=float(record["longitude"]),
                    speed_mps=float(record.get("speed_mps", 0.0)),
                    gps_timestamp=int(record["gps_timestamp"]),
                    snapshot_time=int(record["snapshot_time"]),
                )
            )
        return snapshots

    def _persist_snapshots(self, snapshots: list[VehiclePositionSnapshot]) -> None:
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(snapshot) for snapshot in snapshots]
        self.snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class RealtimeEnrichmentService:
    def __init__(
        self,
        gtfs_static_dir: str | Path,
        ingestion_service: GTFSRealtimeIngestionService,
    ):
        self.gtfs_static_dir = str(gtfs_static_dir)
        self.ingestion_service = ingestion_service
        self.trip_stop_events = load_trip_stop_events(gtfs_static_dir)
        self.segment_live_context: dict[tuple[str, str, str], SegmentLiveContext] = {}
        self.segment_delay_history: dict[tuple[str, str], deque[float]] = defaultdict(
            lambda: deque(maxlen=3)
        )
        self.latest_vehicle_snapshot: dict[str, VehiclePositionSnapshot] = {}
        self.latest_vehicle_observation: dict[str, SegmentObservation] = {}
        self.last_refresh_time: int | None = None
        self.latest_snapshot_time: int | None = None

    def refresh_vehicle_positions(self) -> dict[str, int | None]:
        snapshots = self.ingestion_service.fetch_vehicle_positions()
        enriched_count = 0
        latest_snapshot_time: int | None = None

        for snapshot in snapshots:
            latest_snapshot_time = (
                snapshot.snapshot_time
                if latest_snapshot_time is None
                else max(latest_snapshot_time, snapshot.snapshot_time)
            )
            if self._ingest_snapshot(snapshot):
                enriched_count += 1

        now = int(time.time())
        self.last_refresh_time = now
        self.latest_snapshot_time = latest_snapshot_time
        return {
            "fetched_snapshots": len(snapshots),
            "enriched_segments": enriched_count,
            "latest_snapshot_time": latest_snapshot_time,
        }

    def get_segment_live_context(
        self,
        route_id: str | int,
        from_stop_id: str | int,
        to_stop_id: str | int,
    ) -> SegmentLiveContext | None:
        key = (str(route_id), str(from_stop_id), str(to_stop_id))
        return self.segment_live_context.get(key)

    def get_status(self) -> dict[str, int | bool | None]:
        configured = bool(
            self.ingestion_service.vehicle_positions_url and self.ingestion_service.api_key
        )
        return {
            "configured": configured,
            "last_refresh_time": self.last_refresh_time,
            "latest_snapshot_time": self.latest_snapshot_time,
            "cached_segments": len(self.segment_live_context),
            "cached_vehicles": len(self.latest_vehicle_snapshot),
        }

    def _ingest_snapshot(self, snapshot: VehiclePositionSnapshot) -> bool:
        trip_events = self.trip_stop_events.get(snapshot.trip_id)
        if not trip_events or len(trip_events) < 2:
            return False

        segment_observation = self._infer_segment_observation(snapshot, trip_events)
        if segment_observation is None:
            return False

        key = (
            segment_observation.route_id,
            segment_observation.from_stop_id,
            segment_observation.to_stop_id,
        )
        current_context = self.segment_live_context.get(key)
        if current_context and current_context.last_update_timestamp > snapshot.snapshot_time:
            return False

        trip_segment_key = (snapshot.trip_id, segment_observation.to_stop_id)
        history = self.segment_delay_history[trip_segment_key]
        previous_delay = history[-1] if history else 0.0
        history.append(segment_observation.delay_minutes)
        rolling_delay = sum(history) / len(history)

        self.segment_live_context[key] = SegmentLiveContext(
            route_id=segment_observation.route_id,
            from_stop_id=segment_observation.from_stop_id,
            to_stop_id=segment_observation.to_stop_id,
            prev_segment_delay=previous_delay,
            rolling_segment_delay_3=rolling_delay,
            last_update_timestamp=snapshot.snapshot_time,
            vehicle_id=snapshot.vehicle_id,
            trip_id=snapshot.trip_id,
        )
        self.latest_vehicle_snapshot[snapshot.vehicle_id] = snapshot
        self.latest_vehicle_observation[snapshot.vehicle_id] = segment_observation
        return True

    def _infer_segment_observation(
        self,
        snapshot: VehiclePositionSnapshot,
        trip_events: tuple[TripStopEvent, ...],
    ) -> SegmentObservation | None:
        best_candidate = None
        best_candidate_score = None
        previous_snapshot = self.latest_vehicle_snapshot.get(snapshot.vehicle_id)
        previous_observation = self.latest_vehicle_observation.get(snapshot.vehicle_id)

        for from_event, to_event in zip(trip_events, trip_events[1:]):
            midpoint_lat = (from_event.stop_lat + to_event.stop_lat) / 2.0
            midpoint_lon = (from_event.stop_lon + to_event.stop_lon) / 2.0
            midpoint_distance = haversine_km(
                snapshot.latitude,
                snapshot.longitude,
                midpoint_lat,
                midpoint_lon,
            )

            scheduled_midpoint_unix = scheduled_unix_from_service_date(
                snapshot.start_date,
                from_event.departure_seconds
                + max(0, to_event.arrival_seconds - from_event.departure_seconds) // 2,
            )
            time_alignment_penalty = abs(
                snapshot.gps_timestamp - scheduled_midpoint_unix
            ) / 60.0

            progression_penalty = 0.0
            if previous_snapshot and previous_observation:
                if to_event.stop_sequence < self._to_stop_sequence(
                    previous_observation,
                    trip_events,
                ):
                    progression_penalty += 1_000.0
                previous_distance_to_to_stop = haversine_km(
                    previous_snapshot.latitude,
                    previous_snapshot.longitude,
                    to_event.stop_lat,
                    to_event.stop_lon,
                )
                current_distance_to_to_stop = haversine_km(
                    snapshot.latitude,
                    snapshot.longitude,
                    to_event.stop_lat,
                    to_event.stop_lon,
                )
                if current_distance_to_to_stop > previous_distance_to_to_stop + 0.05:
                    progression_penalty += 5.0

            candidate_score = midpoint_distance + time_alignment_penalty + progression_penalty
            if best_candidate_score is None or candidate_score < best_candidate_score:
                scheduled_arrival_unix = scheduled_unix_from_service_date(
                    snapshot.start_date,
                    to_event.arrival_seconds,
                )
                best_candidate = SegmentObservation(
                    route_id=snapshot.route_id,
                    from_stop_id=from_event.stop_id,
                    to_stop_id=to_event.stop_id,
                    delay_minutes=(
                        snapshot.gps_timestamp - scheduled_arrival_unix
                    )
                    / 60.0,
                    observation_timestamp=snapshot.snapshot_time,
                )
                best_candidate_score = candidate_score

        return best_candidate

    def _to_stop_sequence(
        self,
        observation: SegmentObservation,
        trip_events: tuple[TripStopEvent, ...],
    ) -> int:
        for event in trip_events:
            if event.stop_id == observation.to_stop_id:
                return event.stop_sequence
        return None


_realtime_enrichment_service: RealtimeEnrichmentService | None = None


def get_realtime_enrichment_service() -> RealtimeEnrichmentService:
    global _realtime_enrichment_service
    if _realtime_enrichment_service is None:
        ingestion_service = GTFSRealtimeIngestionService(
            vehicle_positions_url=settings.GTFS_RT_VEHICLE_POSITIONS_URL,
            api_key=settings.GTFS_RT_API_KEY,
            snapshot_path=settings.GTFS_RT_SNAPSHOT_PATH or None,
        )
        _realtime_enrichment_service = RealtimeEnrichmentService(
            gtfs_static_dir=settings.GTFS_STATIC_DIR,
            ingestion_service=ingestion_service,
        )
    return _realtime_enrichment_service
