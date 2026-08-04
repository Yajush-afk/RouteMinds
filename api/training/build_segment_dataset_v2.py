from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from api.training.config import load_training_config, resolve_repo_path
from api.training.data import derive_segment_dataset
from api.training.data_quality import SegmentQualityReport, validate_segment_frame
from api.training.schemas import (
    CANONICAL_SEGMENT_COLUMNS,
    LIVE_FEATURE_COLUMNS,
    ML_V2_SCHEMA_VERSION,
    SegmentDatasetBuildOptions,
)

DELHI_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
DEFAULT_OUTPUT_DIR = "data/processed/ml/segments_v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the canonical RouteMinds ML V2 dataset.")
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--source", choices=("simulation", "realtime"), required=True)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _input_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")
    files = sorted(path.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No Parquet files found under: {path}")
    return [file for file in files if "trace_alignment" not in file.parts]


def _derive_service_date(timestamp: pd.Series) -> pd.Series:
    values = pd.to_datetime(timestamp, unit="s", utc=True, errors="coerce")
    return values.dt.tz_convert(DELHI_TIMEZONE).dt.strftime("%Y%m%d")


def _prepare_source_frame(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    prepared = frame.copy()
    if source == "simulation" and "from_stop_id" not in prepared.columns:
        config = load_training_config("api/training/config/default_config.toml")
        prepared = derive_segment_dataset(prepared, config)

    if "service_date" not in prepared.columns:
        prepared["service_date"] = _derive_service_date(
            pd.to_numeric(prepared["segment_start_scheduled_unix"], errors="coerce")
        )
    prepared["source"] = source
    prepared["route_id"] = prepared["route_id"].astype("string")
    prepared["trip_id"] = prepared["trip_id"].astype("string")
    prepared["from_stop_id"] = prepared["from_stop_id"].astype("string")
    prepared["to_stop_id"] = prepared["to_stop_id"].astype("string")

    confidence_default = 1.0 if source == "simulation" else 0.0
    if "reconstruction_confidence_score" not in prepared.columns:
        prepared["reconstruction_confidence_score"] = confidence_default

    options = SegmentDatasetBuildOptions(source=source)
    if source == "simulation":
        prepared["sample_weight"] = options.synthetic_sample_weight
    else:
        prepared["sample_weight"] = (
            pd.to_numeric(prepared["reconstruction_confidence_score"], errors="coerce")
            .fillna(0.0)
            .clip(0.0, options.realtime_sample_weight)
        )

    live_defaults = {
        "prev_segment_delay": 0.0,
        "rolling_segment_delay_3": 0.0,
        "route_delay_minutes_live": 0.0,
        "segment_slowdown_index": 1.0,
        "corridor_slowdown_score_live": 1.0,
        "headway_irregularity_score_live": 0.0,
        "bunching_indicator": 0.0,
        "live_context_age_seconds": 0.0,
        "live_context_observation_count": 0.0,
        "live_context_available": 0.0,
    }
    for column, default in live_defaults.items():
        if column not in prepared.columns:
            prepared[column] = default
    return prepared


def _merge_reports(reports: Iterable[SegmentQualityReport]) -> dict[str, object]:
    reports = list(reports)
    rejection_counts: dict[str, int] = {}
    for report in reports:
        for reason, count in report.rejection_counts.items():
            rejection_counts[reason] = rejection_counts.get(reason, 0) + count
    return {
        "schema_version": ML_V2_SCHEMA_VERSION,
        "input_rows": sum(report.input_rows for report in reports),
        "accepted_rows": sum(report.accepted_rows for report in reports),
        "rejected_rows": sum(report.rejected_rows for report in reports),
        "rejection_counts": rejection_counts,
        "thresholds": reports[0].thresholds if reports else {},
    }


def build_segment_dataset(
    input_path: str | Path,
    *,
    source: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    overwrite: bool = False,
) -> dict[str, object]:
    resolved_input = resolve_repo_path(str(input_path))
    resolved_output = resolve_repo_path(str(output_dir)) / f"source={source}"
    if resolved_output.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output already exists at {resolved_output}. Pass --overwrite to replace it."
            )
        shutil.rmtree(resolved_output)

    reports: list[SegmentQualityReport] = []
    output_files: list[str] = []
    part_counts: dict[str, int] = {}
    for input_file in _input_files(resolved_input):
        frame = _prepare_source_frame(pd.read_parquet(input_file), source)
        valid, report = validate_segment_frame(frame, source=source)
        reports.append(report)
        if valid.empty:
            continue

        selected_columns = list(CANONICAL_SEGMENT_COLUMNS) + list(LIVE_FEATURE_COLUMNS)
        optional_columns = [
            "actual_segment_start_unix",
            "actual_segment_end_unix",
            "scheduled_headway_minutes",
            "match_strategy",
            "supervised_training_eligible",
        ]
        selected_columns.extend(
            column for column in optional_columns if column in valid.columns
        )
        valid = valid[selected_columns]
        for service_date, partition in valid.groupby("service_date", sort=True):
            partition_dir = resolved_output / f"service_date={service_date}"
            partition_dir.mkdir(parents=True, exist_ok=True)
            part_number = part_counts.get(str(service_date), 0)
            part_counts[str(service_date)] = part_number + 1
            output_path = partition_dir / f"part-{part_number:05d}.parquet"
            partition.to_parquet(output_path, index=False)
            output_files.append(str(output_path))

    payload = {
        **_merge_reports(reports),
        "source": source,
        "input_path": str(resolved_input),
        "output_dir": str(resolved_output),
        "output_files": output_files,
    }
    report_path = resolved_output / "quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    args = parse_args()
    report = build_segment_dataset(
        args.input_path,
        source=args.source,
        output_dir=args.output_dir,
        overwrite=args.overwrite,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
