from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import tomllib
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from api.app.services.gtfs_graph_service import (
    StopNode,
    TripStopEvent,
    haversine_km,
    load_stops,
    load_trip_routes,
    load_trip_stop_events,
)
from api.training.config import REPO_ROOT, resolve_repo_path
from api.training.schemas import ML_V2_SCHEMA_VERSION

DELHI_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
DEFAULT_CONFIG_PATH = "api/training/config/simulation_v2.toml"


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    seed: int
    start_service_date: str
    service_days: int
    max_rows: int
    output_dir: str
    chunk_rows: int
    minimum_free_disk_gb: float


@dataclass(frozen=True, slots=True)
class SlowdownConfig:
    morning_peak_start_hour: int
    morning_peak_end_hour: int
    evening_peak_start_hour: int
    evening_peak_end_hour: int
    morning_peak_multiplier: float
    evening_peak_multiplier: float
    off_peak_multiplier: float
    route_log_sigma: float
    corridor_log_sigma: float
    trip_log_sigma: float
    segment_log_sigma: float
    trip_correlation: float
    minimum_ratio: float
    maximum_ratio: float
    minimum_segment_minutes: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic, chronological GTFS segment simulation data."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--max-rows", type=int)
    parser.add_argument("--output-dir")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def load_config(path: str | Path) -> tuple[SimulationConfig, SlowdownConfig]:
    resolved = resolve_repo_path(str(path))
    with resolved.open("rb") as handle:
        payload = tomllib.load(handle)
    return SimulationConfig(**payload["simulation"]), SlowdownConfig(**payload["slowdown"])


def _service_dates(start_date: str, count: int) -> list[str]:
    start = datetime.strptime(start_date, "%Y%m%d")
    return [(start + timedelta(days=index)).strftime("%Y%m%d") for index in range(count)]


def _service_day_unix(service_date: str) -> int:
    return int(datetime.strptime(service_date, "%Y%m%d").replace(tzinfo=DELHI_TIMEZONE).timestamp())


def _stable_normal(key: str, seed: int, sigma: float) -> float:
    digest = hashlib.sha256(f"{seed}:{key}".encode("utf-8")).digest()
    local_seed = int.from_bytes(digest[:8], "big", signed=False)
    return float(np.random.default_rng(local_seed).normal(0.0, sigma))


def _peak_multiplier(hour: float, config: SlowdownConfig) -> float:
    if config.morning_peak_start_hour <= hour < config.morning_peak_end_hour:
        return config.morning_peak_multiplier
    if config.evening_peak_start_hour <= hour < config.evening_peak_end_hour:
        return config.evening_peak_multiplier
    return config.off_peak_multiplier


def _edge_keys(
    route_id: str,
    events: tuple[TripStopEvent, ...],
) -> set[tuple[str, str, str]]:
    return {
        (route_id, previous.stop_id, current.stop_id)
        for previous, current in zip(events, events[1:])
    }


def _coverage_trip_order(
    trip_events: dict[str, tuple[TripStopEvent, ...]],
    trip_routes: dict[str, str],
    *,
    seed: int,
) -> tuple[list[str], int]:
    trip_ids = [trip_id for trip_id in trip_events if len(trip_events[trip_id]) >= 2]
    rng = np.random.default_rng(seed)
    rng.shuffle(trip_ids)
    uncovered: set[tuple[str, str, str]] = set()
    keys_by_trip: dict[str, set[tuple[str, str, str]]] = {}
    for trip_id in trip_ids:
        keys = _edge_keys(trip_routes[trip_id], trip_events[trip_id])
        keys_by_trip[trip_id] = keys
        uncovered.update(keys)
    total_edges = len(uncovered)

    selected: list[str] = []
    for trip_id in trip_ids:
        if keys_by_trip[trip_id] & uncovered:
            selected.append(trip_id)
            uncovered.difference_update(keys_by_trip[trip_id])
        if not uncovered:
            break
    return selected, total_edges


def _simulate_trip(
    *,
    trip_id: str,
    route_id: str,
    events: tuple[TripStopEvent, ...],
    stops: dict[str, StopNode],
    service_date: str,
    instance: int,
    row_budget: int,
    rng: np.random.Generator,
    simulation_config: SimulationConfig,
    slowdown_config: SlowdownConfig,
) -> list[dict[str, object]]:
    if row_budget <= 0 or len(events) < 2:
        return []

    service_day_start = _service_day_unix(service_date)
    max_stop_sequence = max(event.stop_sequence for event in events)
    route_effect = _stable_normal(
        f"{service_date}:{route_id}",
        simulation_config.seed,
        slowdown_config.route_log_sigma,
    )
    trip_state = float(rng.normal(0.0, slowdown_config.trip_log_sigma))
    actual_cursor = service_day_start + events[0].departure_seconds
    previous_segment_delays: list[float] = []
    rows: list[dict[str, object]] = []

    for previous, current in zip(events, events[1:]):
        if len(rows) >= row_budget:
            break
        scheduled_minutes = (
            current.arrival_seconds - previous.departure_seconds
        ) / 60.0
        if scheduled_minutes <= 0.0:
            continue

        scheduled_start = service_day_start + previous.departure_seconds
        hour = (previous.departure_seconds % 86400) / 3600.0
        peak_log = math.log(_peak_multiplier(hour, slowdown_config))
        corridor_effect = _stable_normal(
            f"{route_id}:{previous.stop_id}:{current.stop_id}",
            simulation_config.seed,
            slowdown_config.corridor_log_sigma,
        )
        trip_state = (
            slowdown_config.trip_correlation * trip_state
            + float(rng.normal(0.0, slowdown_config.trip_log_sigma))
            * math.sqrt(max(0.0, 1.0 - slowdown_config.trip_correlation**2))
        )
        segment_noise = float(rng.normal(0.0, slowdown_config.segment_log_sigma))
        ratio = math.exp(peak_log + route_effect + corridor_effect + trip_state + segment_noise)
        ratio = float(
            np.clip(
                ratio,
                slowdown_config.minimum_ratio,
                slowdown_config.maximum_ratio,
            )
        )
        actual_minutes = max(
            slowdown_config.minimum_segment_minutes,
            scheduled_minutes * ratio,
        )
        actual_start = max(actual_cursor, scheduled_start)
        actual_end = actual_start + int(round(actual_minutes * 60.0))
        actual_minutes = (actual_end - actual_start) / 60.0
        segment_delay = actual_minutes - scheduled_minutes
        previous_delay = previous_segment_delays[-1] if previous_segment_delays else 0.0
        rolling_delay = (
            float(np.mean(previous_segment_delays[-3:]))
            if previous_segment_delays
            else 0.0
        )

        rows.append(
            {
                "service_date": service_date,
                "source": "simulation",
                "trip_id": f"sim:{service_date}:{trip_id}:{instance}",
                "route_id": route_id,
                "from_stop_id": previous.stop_id,
                "to_stop_id": current.stop_id,
                "stop_sequence": current.stop_sequence,
                "normalized_stop_position": (
                    current.stop_sequence / max_stop_sequence if max_stop_sequence else 1.0
                ),
                "distance_to_prev_stop_km": haversine_km(
                    stops[previous.stop_id].stop_lat,
                    stops[previous.stop_id].stop_lon,
                    stops[current.stop_id].stop_lat,
                    stops[current.stop_id].stop_lon,
                ),
                "segment_start_scheduled_unix": scheduled_start,
                "scheduled_segment_minutes": scheduled_minutes,
                "actual_segment_start_unix": actual_start,
                "actual_segment_end_unix": actual_end,
                "actual_segment_minutes": actual_minutes,
                "segment_delay_minutes": segment_delay,
                "prev_segment_delay": previous_delay,
                "rolling_segment_delay_3": rolling_delay,
                "reconstruction_confidence_score": 1.0,
                "sample_weight": 0.25,
            }
        )
        previous_segment_delays.append(segment_delay)
        scheduled_dwell_seconds = max(0, current.departure_seconds - current.arrival_seconds)
        simulated_dwell_seconds = max(
            0,
            scheduled_dwell_seconds + int(round(rng.normal(15.0, 10.0))),
        )
        actual_cursor = actual_end + simulated_dwell_seconds
    return rows


def _flush_rows(
    rows: list[dict[str, object]],
    output_dir: Path,
    part_counts: dict[str, int],
) -> list[str]:
    if not rows:
        return []
    frame = pd.DataFrame(rows)
    output_files: list[str] = []
    for service_date, partition in frame.groupby("service_date", sort=True):
        partition_dir = output_dir / f"service_date={service_date}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        part_number = part_counts.get(str(service_date), 0)
        part_counts[str(service_date)] = part_number + 1
        output_path = partition_dir / f"part-{part_number:05d}.parquet"
        partition.to_parquet(output_path, index=False)
        output_files.append(str(output_path))
    rows.clear()
    return output_files


def generate_simulation(
    simulation_config: SimulationConfig,
    slowdown_config: SlowdownConfig,
    *,
    max_rows: int | None = None,
    output_dir: str | Path | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    row_limit = max_rows or simulation_config.max_rows
    resolved_output = resolve_repo_path(str(output_dir or simulation_config.output_dir))
    if resolved_output.exists():
        if not overwrite:
            raise FileExistsError(
                f"Simulation output exists at {resolved_output}. Pass --overwrite to replace it."
            )
        shutil.rmtree(resolved_output)

    free_gb = shutil.disk_usage(resolved_output.parent).free / (1024**3)
    if free_gb < simulation_config.minimum_free_disk_gb:
        raise RuntimeError(
            f"Only {free_gb:.1f} GiB is free; at least "
            f"{simulation_config.minimum_free_disk_gb:.1f} GiB is required."
        )

    gtfs_dir = REPO_ROOT / "data" / "raw"
    stops = load_stops(gtfs_dir)
    trip_routes = load_trip_routes(gtfs_dir)
    trip_events = load_trip_stop_events(
        gtfs_dir,
        stops_by_id=stops,
        trip_routes=trip_routes,
    )
    coverage_trips, unique_edge_count = _coverage_trip_order(
        trip_events,
        trip_routes,
        seed=simulation_config.seed,
    )
    all_trip_ids = sorted(trip_id for trip_id, events in trip_events.items() if len(events) >= 2)
    service_dates = _service_dates(
        simulation_config.start_service_date,
        simulation_config.service_days,
    )
    rng = np.random.default_rng(simulation_config.seed)

    rows: list[dict[str, object]] = []
    output_files: list[str] = []
    part_counts: dict[str, int] = {}
    generated_rows = 0
    generated_edge_keys: set[tuple[str, str, str]] = set()
    trip_instance = 0
    queue = list(coverage_trips)
    while generated_rows < row_limit:
        if queue:
            trip_id = queue.pop(0)
        else:
            trip_id = str(rng.choice(all_trip_ids))
        events = trip_events[trip_id]
        route_id = trip_routes[trip_id]
        service_date = service_dates[trip_instance % len(service_dates)]
        trip_rows = _simulate_trip(
            trip_id=trip_id,
            route_id=route_id,
            events=events,
            stops=stops,
            service_date=service_date,
            instance=trip_instance,
            row_budget=row_limit - generated_rows,
            rng=rng,
            simulation_config=simulation_config,
            slowdown_config=slowdown_config,
        )
        rows.extend(trip_rows)
        generated_rows += len(trip_rows)
        generated_edge_keys.update(
            (str(row["route_id"]), str(row["from_stop_id"]), str(row["to_stop_id"]))
            for row in trip_rows
        )
        trip_instance += 1
        if len(rows) >= simulation_config.chunk_rows:
            output_files.extend(_flush_rows(rows, resolved_output, part_counts))
        if not trip_rows and not queue:
            break

    output_files.extend(_flush_rows(rows, resolved_output, part_counts))
    manifest = {
        "schema_version": ML_V2_SCHEMA_VERSION,
        "generator": "gtfs_cumulative_segment_simulation_v2",
        "simulation": asdict(simulation_config),
        "slowdown": asdict(slowdown_config),
        "requested_rows": row_limit,
        "generated_rows": generated_rows,
        "service_dates": service_dates,
        "unique_gtfs_edges": unique_edge_count,
        "covered_edges": len(generated_edge_keys),
        "edge_coverage_fraction": (
            len(generated_edge_keys) / unique_edge_count if unique_edge_count else 0.0
        ),
        "output_files": output_files,
    }
    resolved_output.mkdir(parents=True, exist_ok=True)
    (resolved_output / "simulation_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    args = parse_args()
    simulation_config, slowdown_config = load_config(args.config)
    manifest = generate_simulation(
        simulation_config,
        slowdown_config,
        max_rows=args.max_rows,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
