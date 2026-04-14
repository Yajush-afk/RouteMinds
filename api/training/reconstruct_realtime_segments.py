from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from api.app.services.realtime_enrichment_service import (
    DELHI_TIMEZONE,
    TripStopEvent,
    VehiclePositionSnapshot,
    haversine_km,
    load_trip_stop_events,
    scheduled_unix_from_service_date,
)
from api.training.config import resolve_repo_path

DEFAULT_INPUT_DIR = "data/processed/realtime/canonical_snapshots_v2"
DEFAULT_OUTPUT_DIR = "data/processed/realtime/reconstructed_segments_v1"
DEFAULT_REPORT_PATH = "artifacts/metrics/realtime_segment_reconstruction_report_v1.json"
DEFAULT_GTFS_STATIC_DIR = "data/raw"
DEFAULT_MAX_SERVICE_DATES = 0

TRACE_GROUP_COLUMNS = [
    "service_date",
    "route_id",
    "trip_id",
    "vehicle_id",
    "start_date",
    "start_time",
]

TRACE_SORT_COLUMNS = [
    "gps_timestamp",
    "snapshot_timestamp_unix",
]

OUTPUT_COLUMNS = [
    "service_date",
    "realtime_route_id",
    "realtime_trip_id",
    "static_route_id",
    "static_trip_id",
    "match_strategy",
    "route_id",
    "trip_id",
    "vehicle_id",
    "start_date",
    "start_time",
    "trip_start_scheduled_unix",
    "from_stop_id",
    "to_stop_id",
    "from_stop_sequence",
    "stop_sequence",
    "normalized_stop_position",
    "distance_to_prev_stop_km",
    "segment_start_scheduled_unix",
    "scheduled_departure_unix",
    "scheduled_arrival_unix",
    "actual_segment_start_unix",
    "actual_segment_end_unix",
    "scheduled_segment_minutes",
    "actual_segment_minutes",
    "segment_delay_minutes",
    "used_estimated_start_boundary",
    "used_estimated_end_boundary",
    "segment_snapshot_count",
    "reconstruction_confidence_score",
    "supervised_training_eligible",
]

ALIGNMENT_SUMMARY_COLUMNS = [
    "service_date",
    "realtime_route_id",
    "realtime_trip_id",
    "vehicle_id",
    "start_date",
    "effective_start_date",
    "start_time",
    "match_strategy",
    "candidate_count",
    "candidate_static_route_ids",
    "candidate_static_trip_ids",
]


@dataclass(frozen=True, slots=True)
class TripTemplateBundle:
    static_trip_id: str
    static_route_id: str
    public_route_number: str | None
    start_time_key: str
    segment_templates: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class MatchResolution:
    bundle: TripTemplateBundle | None
    strategy: str
    candidate_static_route_ids: tuple[str, ...] = ()
    candidate_static_trip_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InferredSegmentSnapshot:
    static_route_id: str
    static_trip_id: str
    start_date: str
    from_stop_id: str
    to_stop_id: str
    from_stop_sequence: int
    to_stop_sequence: int
    scheduled_departure_unix: int
    scheduled_arrival_unix: int
    scheduled_segment_minutes: float
    normalized_stop_position: float
    distance_to_prev_stop_km: float


@dataclass(slots=True)
class SegmentRun:
    realtime_route_id: str
    realtime_trip_id: str
    static_route_id: str
    static_trip_id: str
    vehicle_id: str
    service_date: str
    start_date: str
    effective_start_date: str
    start_time: str
    match_strategy: str
    from_stop_id: str
    to_stop_id: str
    from_stop_sequence: int
    to_stop_sequence: int
    scheduled_departure_unix: int
    scheduled_arrival_unix: int
    scheduled_segment_minutes: float
    normalized_stop_position: float
    distance_to_prev_stop_km: float
    start_gps_timestamp: int
    end_gps_timestamp: int
    start_snapshot_timestamp_unix: int
    end_snapshot_timestamp_unix: int
    observation_count: int


@dataclass(slots=True)
class ReconstructionStats:
    service_dates_processed: int = 0
    traces_seen: int = 0
    traces_processed: int = 0
    traces_missing_trip_template: int = 0
    traces_with_effective_date_override: int = 0
    exact_trip_matches: int = 0
    exact_route_start_matches: int = 0
    public_route_start_matches: int = 0
    ambiguous_public_route_matches: int = 0
    unresolved_traces: int = 0
    inferred_snapshots: int = 0
    segment_runs: int = 0
    reconstructed_segments: int = 0
    low_confidence_segments: int = 0
    supervised_training_eligible_segments: int = 0
    estimated_start_boundaries: int = 0
    estimated_end_boundaries: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruct segment-level training rows from canonical GTFS-RT snapshots."
    )
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH)
    parser.add_argument("--gtfs-static-dir", default=DEFAULT_GTFS_STATIC_DIR)
    parser.add_argument(
        "--max-service-dates",
        type=int,
        default=DEFAULT_MAX_SERVICE_DATES,
        help="Optional limit for smoke runs. Use 0 for all service-date partitions.",
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Delete existing output files by overwriting service-date Parquet outputs.",
    )
    return parser.parse_args()


def _build_segment_metadata(
    trip_stop_events: dict[str, tuple[TripStopEvent, ...]],
    route_public_numbers: dict[str, str | None],
) -> dict[str, TripTemplateBundle]:
    metadata_by_trip: dict[str, TripTemplateBundle] = {}
    for trip_id, events in trip_stop_events.items():
        if len(events) < 2:
            continue
        max_stop_sequence = max(event.stop_sequence for event in events)
        segment_metadata: list[dict[str, object]] = []
        for from_event, to_event in zip(events, events[1:]):
            scheduled_segment_minutes = max(
                0.0,
                (to_event.arrival_seconds - from_event.departure_seconds) / 60.0,
            )
            segment_metadata.append(
                {
                    "from_stop_id": from_event.stop_id,
                    "to_stop_id": to_event.stop_id,
                    "from_stop_sequence": from_event.stop_sequence,
                    "to_stop_sequence": to_event.stop_sequence,
                    "scheduled_segment_minutes": scheduled_segment_minutes,
                    "distance_to_prev_stop_km": haversine_km(
                        from_event.stop_lat,
                        from_event.stop_lon,
                        to_event.stop_lat,
                        to_event.stop_lon,
                    ),
                    "normalized_stop_position": (
                        float(to_event.stop_sequence) / float(max_stop_sequence)
                        if max_stop_sequence > 0
                        else 1.0
                    ),
                    "from_stop_lat": from_event.stop_lat,
                    "from_stop_lon": from_event.stop_lon,
                    "to_stop_lat": to_event.stop_lat,
                    "to_stop_lon": to_event.stop_lon,
                    "from_departure_seconds": from_event.departure_seconds,
                    "to_arrival_seconds": to_event.arrival_seconds,
                    "route_id": to_event.route_id,
                }
            )
        static_route_id = str(events[0].route_id)
        metadata_by_trip[trip_id] = TripTemplateBundle(
            static_trip_id=trip_id,
            static_route_id=static_route_id,
            public_route_number=route_public_numbers.get(static_route_id),
            start_time_key=_seconds_to_hh_mm(int(segment_metadata[0]["from_departure_seconds"])),
            segment_templates=tuple(segment_metadata),
        )
    return metadata_by_trip


def _build_route_start_index(
    trip_segments: dict[str, TripTemplateBundle],
) -> dict[tuple[str, str], tuple[TripTemplateBundle, ...]]:
    route_start_index: dict[tuple[str, str], list[TripTemplateBundle]] = defaultdict(list)
    for bundle in trip_segments.values():
        route_start_index[(bundle.static_route_id, bundle.start_time_key)].append(bundle)
    return {key: tuple(value) for key, value in route_start_index.items()}


def _build_public_route_start_index(
    trip_segments: dict[str, TripTemplateBundle],
) -> dict[tuple[str, str], tuple[TripTemplateBundle, ...]]:
    public_route_start_index: dict[tuple[str, str], list[TripTemplateBundle]] = defaultdict(list)
    for bundle in trip_segments.values():
        if not bundle.public_route_number:
            continue
        public_route_start_index[(bundle.public_route_number, bundle.start_time_key)].append(
            bundle
        )
    return {key: tuple(value) for key, value in public_route_start_index.items()}


def _build_public_route_index(
    trip_segments: dict[str, TripTemplateBundle],
) -> dict[str, tuple[TripTemplateBundle, ...]]:
    public_route_index: dict[str, list[TripTemplateBundle]] = defaultdict(list)
    for bundle in trip_segments.values():
        if bundle.public_route_number:
            public_route_index[bundle.public_route_number].append(bundle)
    return {key: tuple(value) for key, value in public_route_index.items()}


def _extract_public_route_number(route_long_name: str | None) -> str | None:
    if not route_long_name:
        return None
    match = re.match(r"^(\d+)", str(route_long_name).strip().upper())
    if match:
        return match.group(1)
    return None


def _load_route_public_numbers(gtfs_static_dir: str | Path) -> dict[str, str | None]:
    routes_path = resolve_repo_path(str(gtfs_static_dir)) / "routes.txt"
    routes_frame = pd.read_csv(
        routes_path,
        dtype={"route_id": "string", "route_long_name": "string"},
        usecols=["route_id", "route_long_name"],
    )
    return {
        str(row.route_id): _extract_public_route_number(row.route_long_name)
        for row in routes_frame.itertuples(index=False)
    }


def _candidate_ids(
    bundles: tuple[TripTemplateBundle, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    route_ids = tuple(sorted({bundle.static_route_id for bundle in bundles}))
    trip_ids = tuple(sorted(bundle.static_trip_id for bundle in bundles))
    return route_ids, trip_ids


def _trace_alignment_record(
    *,
    group_key: tuple[object, ...],
    resolution: MatchResolution,
    effective_start_date: str,
) -> dict[str, object]:
    return {
        "service_date": str(group_key[0]),
        "realtime_route_id": str(group_key[1]),
        "realtime_trip_id": str(group_key[2]),
        "vehicle_id": str(group_key[3]),
        "start_date": str(group_key[4]),
        "effective_start_date": effective_start_date,
        "start_time": str(group_key[5]),
        "match_strategy": resolution.strategy,
        "candidate_count": len(resolution.candidate_static_trip_ids),
        "candidate_static_route_ids": list(resolution.candidate_static_route_ids),
        "candidate_static_trip_ids": list(resolution.candidate_static_trip_ids),
    }


def _seconds_to_hh_mm(seconds_from_midnight: int) -> str:
    hours = seconds_from_midnight // 3600
    minutes = (seconds_from_midnight % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def _timestamp_to_service_date(gps_timestamp: int) -> str:
    return datetime.fromtimestamp(gps_timestamp, tz=DELHI_TIMEZONE).strftime("%Y%m%d")


def _parse_yyyymmdd(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d").replace(tzinfo=DELHI_TIMEZONE)


def _resolve_effective_start_date(raw_start_date: str, gps_timestamp: int) -> tuple[str, bool]:
    timestamp_service_date = _timestamp_to_service_date(gps_timestamp)
    try:
        raw_date = _parse_yyyymmdd(raw_start_date)
        inferred_date = _parse_yyyymmdd(timestamp_service_date)
    except ValueError:
        return timestamp_service_date, True

    if abs((inferred_date - raw_date).days) > 1:
        return timestamp_service_date, True
    return raw_start_date, False


def _infer_segment_snapshot(
    *,
    snapshot: VehiclePositionSnapshot,
    bundle: TripTemplateBundle,
    effective_start_date: str,
    segment_templates: tuple[dict[str, object], ...],
    previous_snapshot: VehiclePositionSnapshot | None,
    previous_inferred: InferredSegmentSnapshot | None,
) -> InferredSegmentSnapshot | None:
    best_candidate: InferredSegmentSnapshot | None = None
    best_candidate_score: float | None = None

    for template in segment_templates:
        midpoint_lat = (float(template["from_stop_lat"]) + float(template["to_stop_lat"])) / 2.0
        midpoint_lon = (float(template["from_stop_lon"]) + float(template["to_stop_lon"])) / 2.0
        midpoint_distance = haversine_km(
            snapshot.latitude,
            snapshot.longitude,
            midpoint_lat,
            midpoint_lon,
        )
        midpoint_seconds = int(template["from_departure_seconds"]) + max(
            0,
            int(template["to_arrival_seconds"]) - int(template["from_departure_seconds"]),
        ) // 2
        scheduled_midpoint_unix = scheduled_unix_from_service_date(
            effective_start_date,
            midpoint_seconds,
        )
        time_alignment_penalty = abs(snapshot.gps_timestamp - scheduled_midpoint_unix) / 60.0

        progression_penalty = 0.0
        if previous_snapshot is not None and previous_inferred is not None:
            if int(template["to_stop_sequence"]) < previous_inferred.to_stop_sequence:
                progression_penalty += 1_000.0
            previous_distance_to_to_stop = haversine_km(
                previous_snapshot.latitude,
                previous_snapshot.longitude,
                float(template["to_stop_lat"]),
                float(template["to_stop_lon"]),
            )
            current_distance_to_to_stop = haversine_km(
                snapshot.latitude,
                snapshot.longitude,
                float(template["to_stop_lat"]),
                float(template["to_stop_lon"]),
            )
            if current_distance_to_to_stop > previous_distance_to_to_stop + 0.05:
                progression_penalty += 5.0

        candidate_score = midpoint_distance + time_alignment_penalty + progression_penalty
        if best_candidate_score is not None and candidate_score >= best_candidate_score:
            continue

        best_candidate_score = candidate_score
        best_candidate = InferredSegmentSnapshot(
            static_route_id=bundle.static_route_id,
            static_trip_id=bundle.static_trip_id,
            start_date=snapshot.start_date,
            from_stop_id=str(template["from_stop_id"]),
            to_stop_id=str(template["to_stop_id"]),
            from_stop_sequence=int(template["from_stop_sequence"]),
            to_stop_sequence=int(template["to_stop_sequence"]),
            scheduled_departure_unix=scheduled_unix_from_service_date(
                effective_start_date,
                int(template["from_departure_seconds"]),
            ),
            scheduled_arrival_unix=scheduled_unix_from_service_date(
                effective_start_date,
                int(template["to_arrival_seconds"]),
            ),
            scheduled_segment_minutes=float(template["scheduled_segment_minutes"]),
            normalized_stop_position=float(template["normalized_stop_position"]),
            distance_to_prev_stop_km=float(template["distance_to_prev_stop_km"]),
        )

    return best_candidate


def _build_segment_runs_for_trace(
    trace_frame: pd.DataFrame,
    *,
    bundle: TripTemplateBundle,
    resolution: MatchResolution,
    effective_start_date: str,
    stats: ReconstructionStats,
) -> list[SegmentRun]:
    runs: list[SegmentRun] = []
    previous_snapshot: VehiclePositionSnapshot | None = None
    previous_inferred: InferredSegmentSnapshot | None = None

    for row in trace_frame.itertuples(index=False):
        snapshot = VehiclePositionSnapshot(
            vehicle_id=str(row.vehicle_id),
            trip_id=str(row.trip_id),
            route_id=str(row.route_id),
            start_time=str(row.start_time),
            start_date=str(row.start_date),
            latitude=float(row.latitude),
            longitude=float(row.longitude),
            speed_mps=float(row.speed_mps),
            gps_timestamp=int(row.gps_timestamp),
            snapshot_time=int(row.snapshot_timestamp_unix),
        )
        inferred = _infer_segment_snapshot(
            snapshot=snapshot,
            bundle=bundle,
            effective_start_date=effective_start_date,
            segment_templates=bundle.segment_templates,
            previous_snapshot=previous_snapshot,
            previous_inferred=previous_inferred,
        )
        previous_snapshot = snapshot
        if inferred is None:
            continue
        stats.inferred_snapshots += 1

        if runs and (
            runs[-1].from_stop_id == inferred.from_stop_id
            and runs[-1].to_stop_id == inferred.to_stop_id
        ):
            runs[-1].end_gps_timestamp = snapshot.gps_timestamp
            runs[-1].end_snapshot_timestamp_unix = snapshot.snapshot_time
            runs[-1].observation_count += 1
        else:
            runs.append(
                SegmentRun(
                    realtime_route_id=snapshot.route_id,
                    realtime_trip_id=snapshot.trip_id,
                    static_route_id=inferred.static_route_id,
                    static_trip_id=inferred.static_trip_id,
                    vehicle_id=snapshot.vehicle_id,
                    service_date=str(getattr(row, "service_date")),
                    start_date=snapshot.start_date,
                    effective_start_date=effective_start_date,
                    start_time=snapshot.start_time,
                    match_strategy=resolution.strategy,
                    from_stop_id=inferred.from_stop_id,
                    to_stop_id=inferred.to_stop_id,
                    from_stop_sequence=inferred.from_stop_sequence,
                    to_stop_sequence=inferred.to_stop_sequence,
                    scheduled_departure_unix=inferred.scheduled_departure_unix,
                    scheduled_arrival_unix=inferred.scheduled_arrival_unix,
                    scheduled_segment_minutes=inferred.scheduled_segment_minutes,
                    normalized_stop_position=inferred.normalized_stop_position,
                    distance_to_prev_stop_km=inferred.distance_to_prev_stop_km,
                    start_gps_timestamp=snapshot.gps_timestamp,
                    end_gps_timestamp=snapshot.gps_timestamp,
                    start_snapshot_timestamp_unix=snapshot.snapshot_time,
                    end_snapshot_timestamp_unix=snapshot.snapshot_time,
                    observation_count=1,
                )
            )
        previous_inferred = inferred

    stats.segment_runs += len(runs)
    return runs


def _boundary_timestamp(prev_run: SegmentRun, next_run: SegmentRun) -> int | None:
    if prev_run.to_stop_id != next_run.from_stop_id:
        return None
    if prev_run.to_stop_sequence + 1 != next_run.to_stop_sequence:
        return None
    return int(round((prev_run.end_gps_timestamp + next_run.start_gps_timestamp) / 2.0))


def _reconstruction_confidence(
    *,
    actual_segment_minutes: float,
    scheduled_segment_minutes: float,
    used_estimated_start_boundary: bool,
    used_estimated_end_boundary: bool,
    observation_count: int,
) -> float:
    confidence = 1.0
    if used_estimated_start_boundary:
        confidence -= 0.25
    if used_estimated_end_boundary:
        confidence -= 0.25
    if observation_count <= 1:
        confidence -= 0.15
    if scheduled_segment_minutes > 0.0:
        ratio = actual_segment_minutes / scheduled_segment_minutes
        if ratio < 0.33 or ratio > 3.5:
            confidence -= 0.15
        elif ratio < 0.5 or ratio > 2.5:
            confidence -= 0.08
    return max(0.05, min(0.99, confidence))


def _is_supervised_training_eligible(
    *,
    confidence: float,
    used_estimated_start_boundary: bool,
    used_estimated_end_boundary: bool,
    observation_count: int,
) -> bool:
    return (
        confidence >= 0.7
        and not used_estimated_start_boundary
        and not used_estimated_end_boundary
        and observation_count >= 1
    )


def _reconstruct_segments_from_runs(
    runs: list[SegmentRun],
    *,
    stats: ReconstructionStats,
) -> list[dict[str, object]]:
    if not runs:
        return []

    start_boundaries: list[int | None] = [None] * len(runs)
    end_boundaries: list[int | None] = [None] * len(runs)

    for index in range(len(runs) - 1):
        boundary = _boundary_timestamp(runs[index], runs[index + 1])
        if boundary is None:
            continue
        end_boundaries[index] = boundary
        start_boundaries[index + 1] = boundary

    trip_start_scheduled_unix = min(run.scheduled_departure_unix for run in runs)
    rows: list[dict[str, object]] = []
    for index, run in enumerate(runs):
        actual_start_unix = start_boundaries[index]
        actual_end_unix = end_boundaries[index]
        used_estimated_start_boundary = False
        used_estimated_end_boundary = False

        if actual_start_unix is None:
            if actual_end_unix is not None:
                actual_start_unix = int(
                    round(actual_end_unix - (run.scheduled_segment_minutes * 60.0))
                )
            else:
                actual_start_unix = int(
                    round(run.start_gps_timestamp - (run.scheduled_segment_minutes * 30.0))
                )
            used_estimated_start_boundary = True
            stats.estimated_start_boundaries += 1

        if actual_end_unix is None:
            if actual_start_unix is not None:
                actual_end_unix = int(
                    round(actual_start_unix + (run.scheduled_segment_minutes * 60.0))
                )
            else:
                actual_end_unix = int(
                    round(run.end_gps_timestamp + (run.scheduled_segment_minutes * 30.0))
                )
            used_estimated_end_boundary = True
            stats.estimated_end_boundaries += 1

        if actual_end_unix <= actual_start_unix:
            continue

        actual_segment_minutes = (actual_end_unix - actual_start_unix) / 60.0
        if actual_segment_minutes <= 0.0 or actual_segment_minutes > 120.0:
            continue

        confidence = _reconstruction_confidence(
            actual_segment_minutes=actual_segment_minutes,
            scheduled_segment_minutes=run.scheduled_segment_minutes,
            used_estimated_start_boundary=used_estimated_start_boundary,
            used_estimated_end_boundary=used_estimated_end_boundary,
            observation_count=run.observation_count,
        )
        if confidence < 0.5:
            stats.low_confidence_segments += 1
        supervised_training_eligible = _is_supervised_training_eligible(
            confidence=confidence,
            used_estimated_start_boundary=used_estimated_start_boundary,
            used_estimated_end_boundary=used_estimated_end_boundary,
            observation_count=run.observation_count,
        )
        if supervised_training_eligible:
            stats.supervised_training_eligible_segments += 1

        rows.append(
            {
                "service_date": run.service_date,
                "realtime_route_id": run.realtime_route_id,
                "realtime_trip_id": run.realtime_trip_id,
                "static_route_id": run.static_route_id,
                "static_trip_id": run.static_trip_id,
                "match_strategy": run.match_strategy,
                "route_id": run.static_route_id,
                "trip_id": run.static_trip_id,
                "vehicle_id": run.vehicle_id,
                "start_date": run.start_date,
                "effective_start_date": run.effective_start_date,
                "start_time": run.start_time,
                "trip_start_scheduled_unix": trip_start_scheduled_unix,
                "from_stop_id": run.from_stop_id,
                "to_stop_id": run.to_stop_id,
                "from_stop_sequence": run.from_stop_sequence,
                "stop_sequence": run.to_stop_sequence,
                "normalized_stop_position": run.normalized_stop_position,
                "distance_to_prev_stop_km": run.distance_to_prev_stop_km,
                "segment_start_scheduled_unix": run.scheduled_departure_unix,
                "scheduled_departure_unix": run.scheduled_departure_unix,
                "scheduled_arrival_unix": run.scheduled_arrival_unix,
                "actual_segment_start_unix": actual_start_unix,
                "actual_segment_end_unix": actual_end_unix,
                "scheduled_segment_minutes": run.scheduled_segment_minutes,
                "actual_segment_minutes": actual_segment_minutes,
                "segment_delay_minutes": (
                    actual_segment_minutes - run.scheduled_segment_minutes
                ),
                "used_estimated_start_boundary": used_estimated_start_boundary,
                "used_estimated_end_boundary": used_estimated_end_boundary,
                "segment_snapshot_count": run.observation_count,
                "reconstruction_confidence_score": confidence,
                "supervised_training_eligible": supervised_training_eligible,
            }
        )

    stats.reconstructed_segments += len(rows)
    return rows


def _load_service_date_frame(service_date_dir: Path) -> pd.DataFrame:
    parquet_files = sorted(service_date_dir.glob("*.parquet"))
    if not parquet_files:
        return pd.DataFrame(columns=[])
    frames = [pd.read_parquet(path) for path in parquet_files]
    frame = pd.concat(frames, ignore_index=True)
    return frame.sort_values(TRACE_GROUP_COLUMNS + TRACE_SORT_COLUMNS).reset_index(drop=True)


def _resolve_trace_alignment(
    *,
    group_key: tuple[object, ...],
    trip_segments: dict[str, TripTemplateBundle],
    route_start_index: dict[tuple[str, str], tuple[TripTemplateBundle, ...]],
    public_route_start_index: dict[tuple[str, str], tuple[TripTemplateBundle, ...]],
    public_route_index: dict[str, tuple[TripTemplateBundle, ...]],
) -> MatchResolution:
    realtime_route_id = str(group_key[1])
    realtime_trip_id = str(group_key[2])
    start_time_key = str(group_key[5])[:5]

    exact_bundle = trip_segments.get(realtime_trip_id)
    if exact_bundle:
        return MatchResolution(
            bundle=exact_bundle,
            strategy="exact_trip_id",
            candidate_static_route_ids=(exact_bundle.static_route_id,),
            candidate_static_trip_ids=(exact_bundle.static_trip_id,),
        )

    route_start_candidates = route_start_index.get((realtime_route_id, start_time_key), ())
    if len(route_start_candidates) == 1:
        bundle = route_start_candidates[0]
        return MatchResolution(
            bundle=bundle,
            strategy="exact_route_start",
            candidate_static_route_ids=(bundle.static_route_id,),
            candidate_static_trip_ids=(bundle.static_trip_id,),
        )
    if len(route_start_candidates) > 1:
        route_ids, trip_ids = _candidate_ids(route_start_candidates)
        return MatchResolution(
            bundle=None,
            strategy="ambiguous_exact_route_start",
            candidate_static_route_ids=route_ids,
            candidate_static_trip_ids=trip_ids,
        )

    public_route_start_candidates = public_route_start_index.get(
        (realtime_route_id, start_time_key),
        (),
    )
    if len(public_route_start_candidates) == 1:
        bundle = public_route_start_candidates[0]
        return MatchResolution(
            bundle=bundle,
            strategy="public_route_start_unique",
            candidate_static_route_ids=(bundle.static_route_id,),
            candidate_static_trip_ids=(bundle.static_trip_id,),
        )
    if len(public_route_start_candidates) > 1:
        route_ids, trip_ids = _candidate_ids(public_route_start_candidates)
        return MatchResolution(
            bundle=None,
            strategy="public_route_start_ambiguous",
            candidate_static_route_ids=route_ids,
            candidate_static_trip_ids=trip_ids,
        )

    public_route_candidates = public_route_index.get(realtime_route_id, ())
    if public_route_candidates:
        route_ids, trip_ids = _candidate_ids(public_route_candidates)
        return MatchResolution(
            bundle=None,
            strategy="public_route_candidates_only",
            candidate_static_route_ids=route_ids,
            candidate_static_trip_ids=trip_ids,
        )

    return MatchResolution(bundle=None, strategy="unresolved")


def _update_alignment_stats(stats: ReconstructionStats, resolution: MatchResolution) -> None:
    if resolution.strategy == "exact_trip_id":
        stats.exact_trip_matches += 1
    elif resolution.strategy == "exact_route_start":
        stats.exact_route_start_matches += 1
    elif resolution.strategy == "public_route_start_unique":
        stats.public_route_start_matches += 1
    elif resolution.strategy in {"public_route_start_ambiguous", "public_route_candidates_only", "ambiguous_exact_route_start"}:
        stats.ambiguous_public_route_matches += 1
    elif resolution.strategy == "unresolved":
        stats.unresolved_traces += 1


def reconstruct_segments_for_service_date(
    service_date_frame: pd.DataFrame,
    *,
    trip_segments: dict[str, TripTemplateBundle],
    route_start_index: dict[tuple[str, str], tuple[TripTemplateBundle, ...]],
    public_route_start_index: dict[tuple[str, str], tuple[TripTemplateBundle, ...]],
    public_route_index: dict[str, tuple[TripTemplateBundle, ...]],
    stats: ReconstructionStats,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if service_date_frame.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS), pd.DataFrame(columns=ALIGNMENT_SUMMARY_COLUMNS)

    rows: list[dict[str, object]] = []
    alignment_rows: list[dict[str, object]] = []
    grouped = service_date_frame.groupby(TRACE_GROUP_COLUMNS, sort=False)
    for group_key, trace_frame in grouped:
        stats.traces_seen += 1
        effective_start_date, used_date_override = _resolve_effective_start_date(
            str(group_key[4]),
            int(trace_frame.iloc[0]["gps_timestamp"]),
        )
        if used_date_override:
            stats.traces_with_effective_date_override += 1
        resolution = _resolve_trace_alignment(
            group_key=group_key,
            trip_segments=trip_segments,
            route_start_index=route_start_index,
            public_route_start_index=public_route_start_index,
            public_route_index=public_route_index,
        )
        alignment_rows.append(
            _trace_alignment_record(
                group_key=group_key,
                resolution=resolution,
                effective_start_date=effective_start_date,
            )
        )
        _update_alignment_stats(stats, resolution)
        if resolution.bundle is None:
            stats.traces_missing_trip_template += 1
            continue
        stats.traces_processed += 1
        runs = _build_segment_runs_for_trace(
            trace_frame,
            bundle=resolution.bundle,
            resolution=resolution,
            effective_start_date=effective_start_date,
            stats=stats,
        )
        rows.extend(_reconstruct_segments_from_runs(runs, stats=stats))

    reconstructed_frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=OUTPUT_COLUMNS)
    alignment_frame = pd.DataFrame(alignment_rows) if alignment_rows else pd.DataFrame(columns=ALIGNMENT_SUMMARY_COLUMNS)
    if not reconstructed_frame.empty:
        reconstructed_frame = reconstructed_frame.loc[:, OUTPUT_COLUMNS].sort_values(
            ["service_date", "route_id", "trip_id", "vehicle_id", "segment_start_scheduled_unix"]
        ).reset_index(drop=True)
    if not alignment_frame.empty:
        alignment_frame = alignment_frame.loc[:, ALIGNMENT_SUMMARY_COLUMNS].sort_values(
            ["service_date", "realtime_route_id", "realtime_trip_id", "vehicle_id", "start_time"]
        ).reset_index(drop=True)
    return reconstructed_frame, alignment_frame


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def reconstruct_realtime_segments(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    report_path: str | Path,
    gtfs_static_dir: str | Path,
    max_service_dates: int = 0,
) -> dict[str, object]:
    resolved_input_dir = resolve_repo_path(str(input_dir))
    resolved_output_dir = resolve_repo_path(str(output_dir))
    resolved_report_path = resolve_repo_path(str(report_path))

    if not resolved_input_dir.exists():
        raise FileNotFoundError(
            f"Canonical realtime input directory not found at '{resolved_input_dir}'."
        )

    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    trip_stop_events = load_trip_stop_events(gtfs_static_dir)
    route_public_numbers = _load_route_public_numbers(gtfs_static_dir)
    trip_segments = _build_segment_metadata(trip_stop_events, route_public_numbers)
    route_start_index = _build_route_start_index(trip_segments)
    public_route_start_index = _build_public_route_start_index(trip_segments)
    public_route_index = _build_public_route_index(trip_segments)
    stats = ReconstructionStats()
    output_files: list[str] = []
    alignment_output_dir = resolved_output_dir / "trace_alignment"
    alignment_output_dir.mkdir(parents=True, exist_ok=True)
    alignment_files: list[str] = []

    service_date_dirs = sorted(resolved_input_dir.glob("service_date=*"))
    if max_service_dates > 0:
        service_date_dirs = service_date_dirs[:max_service_dates]

    for service_date_dir in service_date_dirs:
        service_date_value = service_date_dir.name.split("=", 1)[1]
        service_date_frame = _load_service_date_frame(service_date_dir)
        reconstructed_frame, alignment_frame = reconstruct_segments_for_service_date(
            service_date_frame,
            trip_segments=trip_segments,
            route_start_index=route_start_index,
            public_route_start_index=public_route_start_index,
            public_route_index=public_route_index,
            stats=stats,
        )
        stats.service_dates_processed += 1
        output_path = resolved_output_dir / f"service_date={service_date_value}.parquet"
        reconstructed_frame.to_parquet(output_path, index=False)
        output_files.append(str(output_path))
        alignment_path = alignment_output_dir / f"service_date={service_date_value}.parquet"
        alignment_frame.to_parquet(alignment_path, index=False)
        alignment_files.append(str(alignment_path))

    strategy_counts = dict(
        sorted(
            Counter(
                pd.concat(
                    [pd.read_parquet(path, columns=["match_strategy"]) for path in alignment_files],
                    ignore_index=True,
                )["match_strategy"].tolist()
            ).items()
        )
    ) if alignment_files else {}
    report = {
        "input_dir": str(resolved_input_dir),
        "output_dir": str(resolved_output_dir),
        "report_path": str(resolved_report_path),
        "service_dates_processed": stats.service_dates_processed,
        "traces_seen": stats.traces_seen,
        "traces_processed": stats.traces_processed,
        "traces_missing_trip_template": stats.traces_missing_trip_template,
        "traces_with_effective_date_override": stats.traces_with_effective_date_override,
        "exact_trip_matches": stats.exact_trip_matches,
        "exact_route_start_matches": stats.exact_route_start_matches,
        "public_route_start_matches": stats.public_route_start_matches,
        "ambiguous_public_route_matches": stats.ambiguous_public_route_matches,
        "unresolved_traces": stats.unresolved_traces,
        "inferred_snapshots": stats.inferred_snapshots,
        "segment_runs": stats.segment_runs,
        "reconstructed_segments": stats.reconstructed_segments,
        "low_confidence_segments": stats.low_confidence_segments,
        "supervised_training_eligible_segments": stats.supervised_training_eligible_segments,
        "estimated_start_boundaries": stats.estimated_start_boundaries,
        "estimated_end_boundaries": stats.estimated_end_boundaries,
        "strategy_counts": strategy_counts,
        "output_files": output_files,
        "alignment_files": alignment_files,
        "output_columns": OUTPUT_COLUMNS,
        "alignment_columns": ALIGNMENT_SUMMARY_COLUMNS,
    }
    _write_json(resolved_report_path, report)
    return report


def main() -> None:
    args = parse_args()
    report = reconstruct_realtime_segments(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        report_path=args.report_path,
        gtfs_static_dir=args.gtfs_static_dir,
        max_service_dates=args.max_service_dates,
    )
    print("Realtime segment reconstruction finished.")
    print(f"Input: {report['input_dir']}")
    print(f"Output: {report['output_dir']}")
    print(f"Report: {report['report_path']}")
    print(f"Service dates processed: {report['service_dates_processed']}")
    print(f"Traces seen: {report['traces_seen']}")
    print(f"Traces processed: {report['traces_processed']}")
    print(f"Traces missing trip template: {report['traces_missing_trip_template']}")
    print(
        "Traces with effective-date override: "
        f"{report['traces_with_effective_date_override']}"
    )
    print(f"Exact trip matches: {report['exact_trip_matches']}")
    print(f"Exact route+start matches: {report['exact_route_start_matches']}")
    print(f"Public route+start matches: {report['public_route_start_matches']}")
    print(f"Inferred snapshots: {report['inferred_snapshots']}")
    print(f"Segment runs: {report['segment_runs']}")
    print(f"Reconstructed segments: {report['reconstructed_segments']}")
    print(
        "Supervised-training-eligible segments: "
        f"{report['supervised_training_eligible_segments']}"
    )


if __name__ == "__main__":
    main()
