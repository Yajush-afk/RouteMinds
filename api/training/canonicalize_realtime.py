from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from api.training.config import resolve_repo_path

DEFAULT_INPUT_PATH = "data/raw/realtime/realtime_log.csv"
DEFAULT_OUTPUT_DIR = "data/processed/realtime/canonical_snapshots_v2"
DEFAULT_REPORT_PATH = "artifacts/metrics/realtime_canonicalization_report_v2.json"
DEFAULT_CHUNK_ROWS = 100_000

REQUIRED_COLUMNS = (
    "vehicle_id",
    "trip_id",
    "route_id",
    "start_time",
    "start_date",
    "latitude",
    "longitude",
    "speed_mps",
    "gps_timestamp",
    "snapshot_time",
)

CANONICAL_COLUMN_ORDER = [
    "service_date",
    "snapshot_date",
    "vehicle_id",
    "trip_id",
    "route_id",
    "start_time",
    "start_date",
    "latitude",
    "longitude",
    "speed_mps",
    "gps_timestamp",
    "snapshot_time",
    "snapshot_timestamp_unix",
]

DEDUPLICATION_COLUMNS = [
    "vehicle_id",
    "trip_id",
    "route_id",
    "gps_timestamp",
    "snapshot_timestamp_unix",
    "latitude",
    "longitude",
]

SORT_COLUMNS = [
    "service_date",
    "route_id",
    "trip_id",
    "vehicle_id",
    "gps_timestamp",
    "snapshot_timestamp_unix",
]


@dataclass(slots=True)
class ChunkStats:
    raw_rows: int = 0
    canonical_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0


@dataclass(slots=True)
class CanonicalizationReport:
    input_path: str
    output_dir: str
    report_path: str
    chunk_rows: int
    processed_chunks: int
    raw_rows: int
    canonical_rows: int
    invalid_rows_dropped: int
    duplicate_rows_dropped: int
    observed_service_dates: list[str]
    observed_snapshot_dates: list[str]
    observed_route_count: int
    observed_trip_count: int
    observed_vehicle_count: int
    non_zero_speed_rows: int
    min_gps_timestamp: int | None
    max_gps_timestamp: int | None
    min_snapshot_timestamp_unix: int | None
    max_snapshot_timestamp_unix: int | None
    columns: list[str]
    partition_columns: list[str]
    sort_columns: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Canonicalize raw GTFS-RT vehicle-position logs into partitioned Parquet."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT_PATH, help="Raw GTFS-RT CSV path.")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for canonical Parquet partitions.",
    )
    parser.add_argument(
        "--report-path",
        default=DEFAULT_REPORT_PATH,
        help="Path for the canonicalization summary report JSON.",
    )
    parser.add_argument(
        "--chunk-rows",
        type=int,
        default=DEFAULT_CHUNK_ROWS,
        help="Number of CSV rows to process at a time.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional row cap for smoke runs. Use 0 for the full file.",
    )
    parser.add_argument(
        "--overwrite-output",
        action="store_true",
        help="Delete the existing output directory before writing new partitions.",
    )
    return parser.parse_args()


def _require_columns(columns: list[str]) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Realtime dataset is missing required columns: {missing}.")


def _normalize_string_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        frame[column] = frame[column].astype("string").str.strip()


def canonicalize_snapshot_chunk(chunk: pd.DataFrame) -> tuple[pd.DataFrame, ChunkStats]:
    _require_columns(list(chunk.columns))

    frame = chunk.loc[:, list(REQUIRED_COLUMNS)].copy()
    stats = ChunkStats(raw_rows=int(len(frame)))

    _normalize_string_columns(
        frame,
        (
            "vehicle_id",
            "trip_id",
            "route_id",
            "start_time",
            "start_date",
            "snapshot_time",
        ),
    )
    frame["start_date"] = frame["start_date"].str.replace(r"\.0$", "", regex=True)
    frame["start_date"] = frame["start_date"].str.zfill(8)

    for column in ("latitude", "longitude", "speed_mps", "gps_timestamp"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["snapshot_time"] = pd.to_datetime(
        frame["snapshot_time"],
        utc=True,
        errors="coerce",
        format="ISO8601",
    )

    missing_required = pd.Series(False, index=frame.index)
    for column in ("vehicle_id", "trip_id", "route_id", "start_time", "start_date"):
        missing_required |= frame[column].isna() | (frame[column] == "")

    invalid_mask = missing_required
    invalid_mask |= frame["latitude"].isna() | ~frame["latitude"].between(-90.0, 90.0)
    invalid_mask |= frame["longitude"].isna() | ~frame["longitude"].between(-180.0, 180.0)
    invalid_mask |= frame["speed_mps"].isna() | (frame["speed_mps"] < 0.0)
    invalid_mask |= frame["gps_timestamp"].isna() | (frame["gps_timestamp"] <= 0)
    invalid_mask |= frame["snapshot_time"].isna()
    invalid_mask |= ~frame["start_date"].str.fullmatch(r"\d{8}")

    stats.invalid_rows = int(invalid_mask.sum())
    frame = frame.loc[~invalid_mask].copy()

    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMN_ORDER), stats

    frame["route_id"] = frame["route_id"].astype("string")
    frame["vehicle_id"] = frame["vehicle_id"].astype("string")
    frame["trip_id"] = frame["trip_id"].astype("string")
    frame["start_time"] = frame["start_time"].astype("string")
    frame["start_date"] = frame["start_date"].astype("string")
    frame["speed_mps"] = frame["speed_mps"].astype("float32")
    frame["latitude"] = frame["latitude"].astype("float32")
    frame["longitude"] = frame["longitude"].astype("float32")
    frame["gps_timestamp"] = frame["gps_timestamp"].astype("int64")
    frame["snapshot_timestamp_unix"] = (
        frame["snapshot_time"].astype("int64") // 1_000_000_000
    ).astype("int64")
    frame["service_date"] = frame["start_date"]
    frame["snapshot_date"] = frame["snapshot_time"].dt.strftime("%Y%m%d")

    duplicate_mask = frame.duplicated(subset=DEDUPLICATION_COLUMNS, keep="first")
    stats.duplicate_rows = int(duplicate_mask.sum())
    frame = frame.loc[~duplicate_mask].copy()

    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMN_ORDER), stats

    frame = frame.sort_values(SORT_COLUMNS).reset_index(drop=True)
    frame = frame.loc[:, CANONICAL_COLUMN_ORDER]
    stats.canonical_rows = int(len(frame))
    return frame, stats


def _write_partitioned_chunk(
    frame: pd.DataFrame,
    *,
    output_dir: Path,
    partition_counters: dict[str, int],
) -> None:
    if frame.empty:
        return

    grouped = frame.groupby("service_date", sort=False)
    for service_date, partition in grouped:
        partition_key = str(service_date)
        partition_counters[partition_key] += 1
        partition_dir = output_dir / f"service_date={service_date}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        file_path = partition_dir / f"part-{partition_counters[partition_key]:05d}.parquet"
        partition.to_parquet(file_path, index=False)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def canonicalize_realtime_csv(
    *,
    input_path: str | Path,
    output_dir: str | Path,
    report_path: str | Path,
    chunk_rows: int = DEFAULT_CHUNK_ROWS,
    max_rows: int = 0,
    overwrite_output: bool = False,
) -> CanonicalizationReport:
    resolved_input_path = resolve_repo_path(str(input_path))
    resolved_output_dir = resolve_repo_path(str(output_dir))
    resolved_report_path = resolve_repo_path(str(report_path))

    if not resolved_input_path.exists():
        raise FileNotFoundError(f"Realtime CSV not found at '{resolved_input_path}'.")

    if resolved_output_dir.exists():
        if not overwrite_output:
            raise FileExistsError(
                f"Output directory '{resolved_output_dir}' already exists. "
                "Use --overwrite-output to replace it."
            )
        shutil.rmtree(resolved_output_dir)

    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    processed_chunks = 0
    total_raw_rows = 0
    total_invalid_rows = 0
    total_duplicate_rows = 0
    total_canonical_rows = 0
    non_zero_speed_rows = 0
    min_gps_timestamp: int | None = None
    max_gps_timestamp: int | None = None
    min_snapshot_timestamp_unix: int | None = None
    max_snapshot_timestamp_unix: int | None = None
    observed_service_dates: set[str] = set()
    observed_snapshot_dates: set[str] = set()
    observed_routes: set[str] = set()
    observed_trips: set[str] = set()
    observed_vehicles: set[str] = set()
    partition_counters: dict[str, int] = defaultdict(int)

    csv_reader = pd.read_csv(
        resolved_input_path,
        usecols=list(REQUIRED_COLUMNS),
        chunksize=chunk_rows,
        dtype={
            "vehicle_id": "string",
            "trip_id": "string",
            "route_id": "string",
            "start_time": "string",
            "start_date": "string",
            "snapshot_time": "string",
        },
    )

    rows_seen = 0
    for chunk in csv_reader:
        if max_rows > 0 and rows_seen >= max_rows:
            break
        if max_rows > 0:
            remaining_rows = max_rows - rows_seen
            if remaining_rows <= 0:
                break
            if len(chunk) > remaining_rows:
                chunk = chunk.head(remaining_rows).copy()

        canonical_chunk, stats = canonicalize_snapshot_chunk(chunk)
        processed_chunks += 1
        rows_seen += stats.raw_rows
        total_raw_rows += stats.raw_rows
        total_invalid_rows += stats.invalid_rows
        total_duplicate_rows += stats.duplicate_rows
        total_canonical_rows += stats.canonical_rows

        if not canonical_chunk.empty:
            observed_service_dates.update(canonical_chunk["service_date"].unique().tolist())
            observed_snapshot_dates.update(canonical_chunk["snapshot_date"].unique().tolist())
            observed_routes.update(canonical_chunk["route_id"].unique().tolist())
            observed_trips.update(canonical_chunk["trip_id"].unique().tolist())
            observed_vehicles.update(canonical_chunk["vehicle_id"].unique().tolist())
            non_zero_speed_rows += int((canonical_chunk["speed_mps"] > 0.0).sum())

            chunk_min_gps = int(canonical_chunk["gps_timestamp"].min())
            chunk_max_gps = int(canonical_chunk["gps_timestamp"].max())
            chunk_min_snapshot = int(canonical_chunk["snapshot_timestamp_unix"].min())
            chunk_max_snapshot = int(canonical_chunk["snapshot_timestamp_unix"].max())
            min_gps_timestamp = (
                chunk_min_gps
                if min_gps_timestamp is None
                else min(min_gps_timestamp, chunk_min_gps)
            )
            max_gps_timestamp = (
                chunk_max_gps
                if max_gps_timestamp is None
                else max(max_gps_timestamp, chunk_max_gps)
            )
            min_snapshot_timestamp_unix = (
                chunk_min_snapshot
                if min_snapshot_timestamp_unix is None
                else min(min_snapshot_timestamp_unix, chunk_min_snapshot)
            )
            max_snapshot_timestamp_unix = (
                chunk_max_snapshot
                if max_snapshot_timestamp_unix is None
                else max(max_snapshot_timestamp_unix, chunk_max_snapshot)
            )

            _write_partitioned_chunk(
                canonical_chunk,
                output_dir=resolved_output_dir,
                partition_counters=partition_counters,
            )

    report = CanonicalizationReport(
        input_path=str(resolved_input_path),
        output_dir=str(resolved_output_dir),
        report_path=str(resolved_report_path),
        chunk_rows=chunk_rows,
        processed_chunks=processed_chunks,
        raw_rows=total_raw_rows,
        canonical_rows=total_canonical_rows,
        invalid_rows_dropped=total_invalid_rows,
        duplicate_rows_dropped=total_duplicate_rows,
        observed_service_dates=sorted(observed_service_dates),
        observed_snapshot_dates=sorted(observed_snapshot_dates),
        observed_route_count=len(observed_routes),
        observed_trip_count=len(observed_trips),
        observed_vehicle_count=len(observed_vehicles),
        non_zero_speed_rows=non_zero_speed_rows,
        min_gps_timestamp=min_gps_timestamp,
        max_gps_timestamp=max_gps_timestamp,
        min_snapshot_timestamp_unix=min_snapshot_timestamp_unix,
        max_snapshot_timestamp_unix=max_snapshot_timestamp_unix,
        columns=CANONICAL_COLUMN_ORDER,
        partition_columns=["service_date"],
        sort_columns=SORT_COLUMNS,
    )
    _write_json(resolved_report_path, asdict(report))
    return report


def main() -> None:
    args = parse_args()
    report = canonicalize_realtime_csv(
        input_path=args.input,
        output_dir=args.output_dir,
        report_path=args.report_path,
        chunk_rows=args.chunk_rows,
        max_rows=args.max_rows,
        overwrite_output=args.overwrite_output,
    )
    print("Canonicalization finished.")
    print(f"Input: {report.input_path}")
    print(f"Output: {report.output_dir}")
    print(f"Report: {report.report_path}")
    print(f"Processed chunks: {report.processed_chunks}")
    print(f"Raw rows: {report.raw_rows}")
    print(f"Canonical rows: {report.canonical_rows}")
    print(f"Invalid rows dropped: {report.invalid_rows_dropped}")
    print(f"Duplicate rows dropped: {report.duplicate_rows_dropped}")
    print(f"Observed service dates: {', '.join(report.observed_service_dates[:7])}")
    print(f"Observed routes: {report.observed_route_count}")
    print(f"Observed trips: {report.observed_trip_count}")
    print(f"Observed vehicles: {report.observed_vehicle_count}")


if __name__ == "__main__":
    main()
