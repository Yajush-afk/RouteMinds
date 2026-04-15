from __future__ import annotations

import csv
import json
import math
import statistics
import time
from collections import defaultdict, deque
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock, RLock

import httpx

try:
    from google.transit import gtfs_realtime_pb2
except ImportError:
    gtfs_realtime_pb2 = None

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
    scheduled_segment_minutes: float
    prev_segment_delay: float
    rolling_segment_delay_3: float
    route_delay_minutes_live: float
    segment_slowdown_index: float
    corridor_slowdown_score_live: float
    corridor_instability_score_live: float
    service_quality_score: float
    persistent_unreliability_penalty: float
    bunching_indicator: float
    headway_irregularity_score_live: float
    stop_recent_arrival_gap_minutes: float
    last_update_timestamp: int
    vehicle_id: str
    trip_id: str


@dataclass(frozen=True, slots=True)
class SegmentObservation:
    route_id: str
    from_stop_id: str
    to_stop_id: str
    scheduled_segment_minutes: float
    delay_minutes: float
    observation_timestamp: int


@dataclass(frozen=True, slots=True)
class RouteLiveContext:
    route_id: str
    rolling_route_delay_minutes: float
    corridor_slowdown_score_live: float
    corridor_instability_score_live: float
    service_quality_score: float
    persistent_unreliability_penalty: float
    bunching_indicator: float
    headway_irregularity_score_live: float
    last_update_timestamp: int


@dataclass(frozen=True, slots=True)
class StopLiveContext:
    route_id: str
    stop_id: str
    recent_arrival_gap_minutes: float
    headway_irregularity_score_live: float
    bunching_indicator: float
    last_update_timestamp: int


@dataclass(frozen=True, slots=True)
class RefreshResult:
    fetched_snapshots: int
    enriched_segments: int
    latest_snapshot_time: int | None
    unmatched_snapshots: int
    unmatched_trips: int
    unmatched_vehicles: int
    malformed_records: int
    provider_format: str | None
    auth_mode: str
    last_refresh_successful: bool
    last_refresh_error: str | None


@dataclass(frozen=True, slots=True)
class RealtimeOperationalStatus:
    configured: bool
    last_refresh_time: int | None
    last_successful_refresh_time: int | None
    latest_snapshot_time: int | None
    fetched_snapshots: int
    enriched_segments: int
    unmatched_snapshots: int
    unmatched_trips: int
    unmatched_vehicles: int
    malformed_records: int
    cached_segments: int
    cached_vehicles: int
    cache_max_age_seconds: int
    cache_is_fresh: bool
    provider_format: str | None
    auth_mode: str
    last_refresh_successful: bool
    last_refresh_error: str | None

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


def derive_scheduled_headways_by_route_stop(
    trip_stop_events: dict[str, tuple[TripStopEvent, ...]],
) -> dict[tuple[str, str], float]:
    arrival_seconds_by_route_stop: dict[tuple[str, str], list[int]] = defaultdict(list)
    for events in trip_stop_events.values():
        for event in events:
            arrival_seconds_by_route_stop[(event.route_id, event.stop_id)].append(
                event.arrival_seconds
            )

    scheduled_headways: dict[tuple[str, str], float] = {}
    for key, arrival_seconds in arrival_seconds_by_route_stop.items():
        if len(arrival_seconds) < 2:
            continue
        sorted_arrivals = sorted(arrival_seconds)
        headways_minutes = [
            (current - previous) / 60.0
            for previous, current in zip(sorted_arrivals, sorted_arrivals[1:])
            if current > previous
        ]
        if headways_minutes:
            scheduled_headways[key] = float(statistics.median(headways_minutes))
    return scheduled_headways


class GTFSRealtimeIngestionService:
    def __init__(
        self,
        vehicle_positions_url: str,
        api_key: str,
        snapshot_path: str | Path | None = None,
        auth_mode: str = "auto",
        api_key_query_param: str = "key",
        response_format: str = "auto",
        timeout_seconds: float = 15.0,
    ):
        self.vehicle_positions_url = vehicle_positions_url
        self.api_key = api_key
        self.snapshot_path = (
            resolve_rt_path(snapshot_path) if snapshot_path else None
        )
        self.auth_mode = auth_mode
        self.api_key_query_param = api_key_query_param
        self.response_format = response_format
        self.timeout_seconds = timeout_seconds
        self.last_provider_format: str | None = None
        self.last_raw_record_count = 0
        self.last_malformed_record_count = 0
        self.last_refresh_error: str | None = None
        self.last_http_status_code: int | None = None

    def fetch_vehicle_positions(self) -> list[VehiclePositionSnapshot]:
        if not self.vehicle_positions_url:
            raise GTFSRealtimeException(
                "GTFS real-time vehicle positions URL is not configured."
            )
        if not self.api_key:
            raise GTFSRealtimeException("GTFS real-time API key is not configured.")

        request_kwargs = self._build_request_kwargs()
        try:
            response = httpx.get(
                self.vehicle_positions_url,
                timeout=self.timeout_seconds,
                **request_kwargs,
            )
            self.last_http_status_code = response.status_code
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self.last_refresh_error = (
                f"Unable to fetch GTFS real-time vehicle positions: {exc}"
            )
            raise GTFSRealtimeException(
                self.last_refresh_error
            ) from exc

        snapshots = self._parse_response(response)
        self.last_refresh_error = None
        if self.snapshot_path:
            self._persist_snapshots(snapshots)
        return snapshots

    def _build_request_kwargs(self) -> dict[str, dict[str, str]]:
        auth_mode = self._resolve_auth_mode()
        if auth_mode == "query":
            return {
                "params": {self.api_key_query_param: self.api_key},
                "headers": {},
            }
        return {
            "params": {},
            "headers": {
                "Authorization": self.api_key,
                "x-api-key": self.api_key,
            },
        }

    def _resolve_auth_mode(self) -> str:
        if self.auth_mode != "auto":
            return self.auth_mode
        if self.vehicle_positions_url.lower().endswith(".pb"):
            return "query"
        return "headers"

    def _resolve_response_format(self, response: httpx.Response) -> str:
        if self.response_format != "auto":
            return self.response_format

        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type:
            return "json"
        if "protobuf" in content_type or "octet-stream" in content_type:
            return "protobuf"
        if str(response.request.url).lower().endswith(".pb"):
            return "protobuf"

        try:
            response.json()
            return "json"
        except (ValueError, json.JSONDecodeError):
            return "protobuf"

    def _parse_response(self, response: httpx.Response) -> list[VehiclePositionSnapshot]:
        response_format = self._resolve_response_format(response)
        self.last_provider_format = response_format
        if response_format == "protobuf":
            return self._normalize_protobuf_response(response.content)
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise GTFSRealtimeException(
                "GTFS real-time response is not valid JSON."
            ) from exc
        return self._normalize_json_response(payload)

    def _normalize_json_response(self, payload) -> list[VehiclePositionSnapshot]:
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

        self.last_raw_record_count = len(records)
        self.last_malformed_record_count = 0
        snapshots = []
        for record in records:
            try:
                snapshots.append(
                    VehiclePositionSnapshot(
                        vehicle_id=str(record["vehicle_id"]),
                        trip_id=str(record.get("trip_id", "")),
                        route_id=str(record.get("route_id", "")),
                        start_time=str(record.get("start_time", "")),
                        start_date=str(record["start_date"]),
                        latitude=float(record["latitude"]),
                        longitude=float(record["longitude"]),
                        speed_mps=float(record.get("speed_mps", 0.0)),
                        gps_timestamp=int(record["gps_timestamp"]),
                        snapshot_time=int(record.get("snapshot_time", record["gps_timestamp"])),
                    )
                )
            except (KeyError, TypeError, ValueError):
                self.last_malformed_record_count += 1
                continue
        return snapshots

    def _normalize_protobuf_response(self, payload: bytes) -> list[VehiclePositionSnapshot]:
        if not payload:
            self.last_raw_record_count = 0
            self.last_malformed_record_count = 0
            return []

        if gtfs_realtime_pb2 is None:
            raise GTFSRealtimeException(
                "GTFS real-time protobuf support requires the 'gtfs-realtime-bindings' package."
            )

        feed = gtfs_realtime_pb2.FeedMessage()
        try:
            feed.ParseFromString(payload)
        except Exception as exc:
            raise GTFSRealtimeException(
                "GTFS real-time protobuf payload could not be parsed."
            ) from exc

        feed_timestamp = int(feed.header.timestamp) if feed.header.timestamp else int(time.time())
        entities = list(feed.entity)
        self.last_raw_record_count = len(entities)
        self.last_malformed_record_count = 0
        snapshots: list[VehiclePositionSnapshot] = []
        for entity in entities:
            if not entity.HasField("vehicle"):
                self.last_malformed_record_count += 1
                continue
            vehicle = entity.vehicle
            if not vehicle.HasField("position") or not vehicle.HasField("trip"):
                self.last_malformed_record_count += 1
                continue
            try:
                gps_timestamp = int(vehicle.timestamp) if vehicle.timestamp else feed_timestamp
                snapshot_time = feed_timestamp
                snapshots.append(
                    VehiclePositionSnapshot(
                        vehicle_id=str(vehicle.vehicle.id or entity.id),
                        trip_id=str(vehicle.trip.trip_id),
                        route_id=str(vehicle.trip.route_id),
                        start_time=str(vehicle.trip.start_time),
                        start_date=str(vehicle.trip.start_date),
                        latitude=float(vehicle.position.latitude),
                        longitude=float(vehicle.position.longitude),
                        speed_mps=float(vehicle.position.speed or 0.0),
                        gps_timestamp=gps_timestamp,
                        snapshot_time=snapshot_time,
                    )
                )
            except (TypeError, ValueError):
                self.last_malformed_record_count += 1
                continue
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
        cache_max_age_seconds: int = 300,
    ):
        self.gtfs_static_dir = str(gtfs_static_dir)
        self.ingestion_service = ingestion_service
        self.cache_max_age_seconds = cache_max_age_seconds
        self.trip_stop_events = load_trip_stop_events(gtfs_static_dir)
        self.scheduled_headways_by_route_stop = derive_scheduled_headways_by_route_stop(
            self.trip_stop_events
        )
        self.segment_live_context: dict[tuple[str, str, str], SegmentLiveContext] = {}
        self.route_live_context: dict[str, RouteLiveContext] = {}
        self.stop_live_context: dict[tuple[str, str], StopLiveContext] = {}
        self.segment_delay_history: dict[tuple[str, str], deque[float]] = defaultdict(
            lambda: deque(maxlen=3)
        )
        self.route_delay_history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=10)
        )
        self.route_slowdown_history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=10)
        )
        self.route_headway_irregularity_history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=10)
        )
        self.route_bunching_history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=10)
        )
        self.stop_arrival_history: dict[tuple[str, str], deque[int]] = defaultdict(
            lambda: deque(maxlen=5)
        )
        self.latest_vehicle_snapshot: dict[str, VehiclePositionSnapshot] = {}
        self.latest_vehicle_observation: dict[str, SegmentObservation] = {}
        self.last_refresh_time: int | None = None
        self.last_successful_refresh_time: int | None = None
        self.latest_snapshot_time: int | None = None
        self._refresh_lock = Lock()
        self._state_lock = RLock()
        self.last_refresh_result = RefreshResult(
            fetched_snapshots=0,
            enriched_segments=0,
            latest_snapshot_time=None,
            unmatched_snapshots=0,
            unmatched_trips=0,
            unmatched_vehicles=0,
            malformed_records=0,
            provider_format=None,
            auth_mode=self.ingestion_service._resolve_auth_mode(),
            last_refresh_successful=False,
            last_refresh_error=None,
        )

    def _evict_stale_state(self, reference_timestamp: int) -> None:
        stale_segment_keys = [
            key
            for key, context in self.segment_live_context.items()
            if self._context_is_stale(context, reference_timestamp)
        ]
        for key in stale_segment_keys:
            self.segment_live_context.pop(key, None)

        stale_route_keys = [
            key
            for key, context in self.route_live_context.items()
            if self._context_is_stale(context, reference_timestamp)
        ]
        for key in stale_route_keys:
            self.route_live_context.pop(key, None)

        stale_stop_keys = [
            key
            for key, context in self.stop_live_context.items()
            if self._context_is_stale(context, reference_timestamp)
        ]
        for key in stale_stop_keys:
            self.stop_live_context.pop(key, None)

        stale_vehicle_ids = [
            vehicle_id
            for vehicle_id, snapshot in self.latest_vehicle_snapshot.items()
            if (reference_timestamp - snapshot.snapshot_time) > self.cache_max_age_seconds
        ]
        for vehicle_id in stale_vehicle_ids:
            self.latest_vehicle_snapshot.pop(vehicle_id, None)
            self.latest_vehicle_observation.pop(vehicle_id, None)

        active_trip_keys = {
            (observation.trip_id, observation.to_stop_id)
            for observation in self.latest_vehicle_observation.values()
        }
        stale_history_keys = [
            key for key in self.segment_delay_history if key not in active_trip_keys
        ]
        for key in stale_history_keys:
            self.segment_delay_history.pop(key, None)

        active_route_ids = set(self.route_live_context.keys())
        active_route_stop_keys = set(self.stop_live_context.keys())
        for history_map in (
            self.route_delay_history,
            self.route_slowdown_history,
            self.route_headway_irregularity_history,
            self.route_bunching_history,
        ):
            stale_route_history_keys = [
                key for key in history_map if key not in active_route_ids
            ]
            for key in stale_route_history_keys:
                history_map.pop(key, None)

        stale_stop_arrival_keys = [
            key for key in self.stop_arrival_history if key not in active_route_stop_keys
        ]
        for key in stale_stop_arrival_keys:
            self.stop_arrival_history.pop(key, None)

    def refresh_vehicle_positions(self) -> dict[str, int | bool | str | None]:
        with self._refresh_lock:
            now = int(time.time())
            with self._state_lock:
                self.last_refresh_time = now
                self._evict_stale_state(now)

            unmatched_vehicle_ids: set[str] = set()
            unmatched_trip_ids: set[str] = set()

            try:
                snapshots = self.ingestion_service.fetch_vehicle_positions()
            except GTFSRealtimeException as exc:
                with self._state_lock:
                    self.last_refresh_result = RefreshResult(
                        fetched_snapshots=0,
                        enriched_segments=0,
                        latest_snapshot_time=self.latest_snapshot_time,
                        unmatched_snapshots=0,
                        unmatched_trips=0,
                        unmatched_vehicles=0,
                        malformed_records=self.ingestion_service.last_malformed_record_count,
                        provider_format=self.ingestion_service.last_provider_format,
                        auth_mode=self.ingestion_service._resolve_auth_mode(),
                        last_refresh_successful=False,
                        last_refresh_error=str(exc),
                    )
                raise

            enriched_count = 0
            latest_snapshot_time: int | None = None
            unmatched_snapshots = 0

            with self._state_lock:
                for snapshot in snapshots:
                    latest_snapshot_time = (
                        snapshot.snapshot_time
                        if latest_snapshot_time is None
                        else max(latest_snapshot_time, snapshot.snapshot_time)
                    )
                    ingest_outcome = self._ingest_snapshot(snapshot)
                    if ingest_outcome == "enriched":
                        enriched_count += 1
                        continue
                    unmatched_snapshots += 1
                    unmatched_vehicle_ids.add(snapshot.vehicle_id)
                    if snapshot.trip_id:
                        unmatched_trip_ids.add(snapshot.trip_id)

                self.latest_snapshot_time = latest_snapshot_time
                self.last_successful_refresh_time = now
                self.last_refresh_result = RefreshResult(
                    fetched_snapshots=len(snapshots),
                    enriched_segments=enriched_count,
                    latest_snapshot_time=latest_snapshot_time,
                    unmatched_snapshots=unmatched_snapshots,
                    unmatched_trips=len(unmatched_trip_ids),
                    unmatched_vehicles=len(unmatched_vehicle_ids),
                    malformed_records=self.ingestion_service.last_malformed_record_count,
                    provider_format=self.ingestion_service.last_provider_format,
                    auth_mode=self.ingestion_service._resolve_auth_mode(),
                    last_refresh_successful=True,
                    last_refresh_error=None,
                )
                return asdict(self.last_refresh_result)

    def get_segment_live_context(
        self,
        route_id: str | int,
        from_stop_id: str | int,
        to_stop_id: str | int,
        reference_timestamp: int | None = None,
    ) -> SegmentLiveContext | None:
        key = (str(route_id), str(from_stop_id), str(to_stop_id))
        with self._state_lock:
            context = self.segment_live_context.get(key)
        if context is None:
            return None
        reference_timestamp = reference_timestamp or int(time.time())
        if self._context_is_stale(context, reference_timestamp):
            return None
        return context

    def get_route_live_context(
        self,
        route_id: str | int,
        reference_timestamp: int | None = None,
    ) -> RouteLiveContext | None:
        key = str(route_id)
        with self._state_lock:
            context = self.route_live_context.get(key)
        if context is None:
            return None
        reference_timestamp = reference_timestamp or int(time.time())
        if self._context_is_stale(context, reference_timestamp):
            return None
        return context

    def get_stop_live_context(
        self,
        route_id: str | int,
        stop_id: str | int,
        reference_timestamp: int | None = None,
    ) -> StopLiveContext | None:
        key = (str(route_id), str(stop_id))
        with self._state_lock:
            context = self.stop_live_context.get(key)
        if context is None:
            return None
        reference_timestamp = reference_timestamp or int(time.time())
        if self._context_is_stale(context, reference_timestamp):
            return None
        return context

    def get_scheduled_headway_minutes(
        self,
        route_id: str | int,
        stop_id: str | int,
    ) -> float | None:
        return self.scheduled_headways_by_route_stop.get((str(route_id), str(stop_id)))

    def get_status(self) -> dict[str, int | bool | str | None]:
        configured = bool(
            self.ingestion_service.vehicle_positions_url and self.ingestion_service.api_key
        )
        with self._state_lock:
            status = RealtimeOperationalStatus(
                configured=configured,
                last_refresh_time=self.last_refresh_time,
                last_successful_refresh_time=self.last_successful_refresh_time,
                latest_snapshot_time=self.latest_snapshot_time,
                fetched_snapshots=self.last_refresh_result.fetched_snapshots,
                enriched_segments=self.last_refresh_result.enriched_segments,
                unmatched_snapshots=self.last_refresh_result.unmatched_snapshots,
                unmatched_trips=self.last_refresh_result.unmatched_trips,
                unmatched_vehicles=self.last_refresh_result.unmatched_vehicles,
                malformed_records=self.last_refresh_result.malformed_records,
                cached_segments=len(self.segment_live_context),
                cached_vehicles=len(self.latest_vehicle_snapshot),
                cache_max_age_seconds=self.cache_max_age_seconds,
                cache_is_fresh=self._cache_is_fresh(),
                provider_format=self.last_refresh_result.provider_format,
                auth_mode=self.last_refresh_result.auth_mode,
                last_refresh_successful=self.last_refresh_result.last_refresh_successful,
                last_refresh_error=self.last_refresh_result.last_refresh_error,
            )
            return asdict(status)

    def _derive_route_system_signals(
        self,
        *,
        rolling_route_delay_minutes: float,
        corridor_slowdown_score_live: float,
        headway_irregularity_score_live: float,
        bunching_indicator: float,
    ) -> tuple[float, float, float]:
        corridor_instability_score_live = 0.0
        corridor_instability_score_live += min(0.4, max(0.0, corridor_slowdown_score_live - 1.0) * 0.45)
        corridor_instability_score_live += min(0.25, max(0.0, rolling_route_delay_minutes) / 20.0)
        corridor_instability_score_live += min(0.2, max(0.0, headway_irregularity_score_live) * 0.2)
        corridor_instability_score_live += min(0.15, max(0.0, bunching_indicator) * 0.15)
        corridor_instability_score_live = max(0.0, min(1.0, corridor_instability_score_live))
        service_quality_score = max(0.05, 1.0 - corridor_instability_score_live)
        persistent_unreliability_penalty = min(2.0, corridor_instability_score_live * 2.0)
        return (
            corridor_instability_score_live,
            service_quality_score,
            persistent_unreliability_penalty,
        )

    def _cache_is_fresh(self, reference_timestamp: int | None = None) -> bool:
        if self.latest_snapshot_time is None:
            return False
        reference_timestamp = reference_timestamp or int(time.time())
        return (reference_timestamp - self.latest_snapshot_time) <= self.cache_max_age_seconds

    def _context_is_stale(
        self,
        context: SegmentLiveContext,
        reference_timestamp: int,
    ) -> bool:
        return (reference_timestamp - context.last_update_timestamp) > self.cache_max_age_seconds

    def _ingest_snapshot(self, snapshot: VehiclePositionSnapshot) -> str:
        if not snapshot.trip_id:
            return "missing_trip_id"
        trip_events = self.trip_stop_events.get(snapshot.trip_id)
        if not trip_events or len(trip_events) < 2:
            return "missing_trip_match"

        segment_observation = self._infer_segment_observation(snapshot, trip_events)
        if segment_observation is None:
            return "segment_not_inferred"

        key = (
            segment_observation.route_id,
            segment_observation.from_stop_id,
            segment_observation.to_stop_id,
        )
        current_context = self.segment_live_context.get(key)
        if current_context and current_context.last_update_timestamp > snapshot.snapshot_time:
            return "stale_snapshot"

        trip_segment_key = (snapshot.trip_id, segment_observation.to_stop_id)
        history = self.segment_delay_history[trip_segment_key]
        previous_delay = history[-1] if history else 0.0
        history.append(segment_observation.delay_minutes)
        rolling_delay = sum(history) / len(history)

        route_delay_history = self.route_delay_history[segment_observation.route_id]
        route_delay_history.append(segment_observation.delay_minutes)
        rolling_route_delay = sum(route_delay_history) / len(route_delay_history)

        segment_slowdown_index = self._segment_slowdown_index(segment_observation)
        route_slowdown_history = self.route_slowdown_history[segment_observation.route_id]
        route_slowdown_history.append(segment_slowdown_index)
        corridor_slowdown_score_live = sum(route_slowdown_history) / len(
            route_slowdown_history
        )

        (
            stop_recent_arrival_gap_minutes,
            headway_irregularity_score_live,
            bunching_indicator,
        ) = self._update_stop_and_headway_context(segment_observation)

        route_headway_irregularity_history = self.route_headway_irregularity_history[
            segment_observation.route_id
        ]
        route_headway_irregularity_history.append(headway_irregularity_score_live)
        route_bunching_history = self.route_bunching_history[segment_observation.route_id]
        route_bunching_history.append(bunching_indicator)
        route_bunching_average = sum(route_bunching_history) / len(route_bunching_history)
        route_headway_irregularity_average = (
            sum(route_headway_irregularity_history) / len(route_headway_irregularity_history)
        )
        (
            corridor_instability_score_live,
            service_quality_score,
            persistent_unreliability_penalty,
        ) = self._derive_route_system_signals(
            rolling_route_delay_minutes=rolling_route_delay,
            corridor_slowdown_score_live=corridor_slowdown_score_live,
            headway_irregularity_score_live=route_headway_irregularity_average,
            bunching_indicator=route_bunching_average,
        )

        self.route_live_context[segment_observation.route_id] = RouteLiveContext(
            route_id=segment_observation.route_id,
            rolling_route_delay_minutes=rolling_route_delay,
            corridor_slowdown_score_live=corridor_slowdown_score_live,
            corridor_instability_score_live=corridor_instability_score_live,
            service_quality_score=service_quality_score,
            persistent_unreliability_penalty=persistent_unreliability_penalty,
            bunching_indicator=route_bunching_average,
            headway_irregularity_score_live=route_headway_irregularity_average,
            last_update_timestamp=snapshot.snapshot_time,
        )
        self.stop_live_context[
            (segment_observation.route_id, segment_observation.to_stop_id)
        ] = StopLiveContext(
            route_id=segment_observation.route_id,
            stop_id=segment_observation.to_stop_id,
            recent_arrival_gap_minutes=stop_recent_arrival_gap_minutes,
            headway_irregularity_score_live=headway_irregularity_score_live,
            bunching_indicator=bunching_indicator,
            last_update_timestamp=snapshot.snapshot_time,
        )

        self.segment_live_context[key] = SegmentLiveContext(
            route_id=segment_observation.route_id,
            from_stop_id=segment_observation.from_stop_id,
            to_stop_id=segment_observation.to_stop_id,
            scheduled_segment_minutes=segment_observation.scheduled_segment_minutes,
            prev_segment_delay=previous_delay,
            rolling_segment_delay_3=rolling_delay,
            route_delay_minutes_live=rolling_route_delay,
            segment_slowdown_index=segment_slowdown_index,
            corridor_slowdown_score_live=corridor_slowdown_score_live,
            corridor_instability_score_live=corridor_instability_score_live,
            service_quality_score=service_quality_score,
            persistent_unreliability_penalty=persistent_unreliability_penalty,
            bunching_indicator=bunching_indicator,
            headway_irregularity_score_live=headway_irregularity_score_live,
            stop_recent_arrival_gap_minutes=stop_recent_arrival_gap_minutes,
            last_update_timestamp=snapshot.snapshot_time,
            vehicle_id=snapshot.vehicle_id,
            trip_id=snapshot.trip_id,
        )
        self.latest_vehicle_snapshot[snapshot.vehicle_id] = snapshot
        self.latest_vehicle_observation[snapshot.vehicle_id] = segment_observation
        return "enriched"

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
                    route_id=to_event.route_id,
                    from_stop_id=from_event.stop_id,
                    to_stop_id=to_event.stop_id,
                    scheduled_segment_minutes=max(
                        0.0,
                        (to_event.arrival_seconds - from_event.departure_seconds) / 60.0,
                    ),
                    delay_minutes=(
                        snapshot.gps_timestamp - scheduled_arrival_unix
                    )
                    / 60.0,
                    observation_timestamp=snapshot.snapshot_time,
                )
                best_candidate_score = candidate_score

        return best_candidate

    def _segment_slowdown_index(self, observation: SegmentObservation) -> float:
        baseline_minutes = max(observation.scheduled_segment_minutes, 0.5)
        effective_minutes = max(
            observation.scheduled_segment_minutes + max(observation.delay_minutes, 0.0),
            0.1,
        )
        return effective_minutes / baseline_minutes

    def _update_stop_and_headway_context(
        self,
        observation: SegmentObservation,
    ) -> tuple[float, float, float]:
        stop_key = (observation.route_id, observation.to_stop_id)
        arrivals = self.stop_arrival_history[stop_key]
        recent_arrival_gap_minutes = 0.0
        if arrivals:
            recent_arrival_gap_minutes = max(
                0.0,
                (observation.observation_timestamp - arrivals[-1]) / 60.0,
            )

        scheduled_headway_minutes = self.scheduled_headways_by_route_stop.get(stop_key)
        headway_irregularity_score_live = 0.0
        bunching_indicator = 0.0
        if scheduled_headway_minutes and recent_arrival_gap_minutes > 0.0:
            headway_irregularity_score_live = abs(
                recent_arrival_gap_minutes - scheduled_headway_minutes
            ) / max(scheduled_headway_minutes, 1.0)
            if recent_arrival_gap_minutes < max(1.0, scheduled_headway_minutes * 0.5):
                bunching_indicator = 1.0

        arrivals.append(observation.observation_timestamp)
        return (
            recent_arrival_gap_minutes,
            headway_irregularity_score_live,
            bunching_indicator,
        )

    def _to_stop_sequence(
        self,
        observation: SegmentObservation,
        trip_events: tuple[TripStopEvent, ...],
    ) -> int | None:
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
            auth_mode=settings.GTFS_RT_AUTH_MODE,
            api_key_query_param=settings.GTFS_RT_API_KEY_QUERY_PARAM,
            response_format=settings.GTFS_RT_RESPONSE_FORMAT,
        )
        _realtime_enrichment_service = RealtimeEnrichmentService(
            gtfs_static_dir=settings.GTFS_STATIC_DIR,
            ingestion_service=ingestion_service,
            cache_max_age_seconds=settings.GTFS_RT_CACHE_MAX_AGE_SECONDS,
        )
    return _realtime_enrichment_service
