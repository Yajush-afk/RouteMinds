from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from api.training.schemas import SegmentQualityThresholds


@dataclass(slots=True)
class SegmentQualityReport:
    input_rows: int
    accepted_rows: int = 0
    rejected_rows: int = 0
    rejection_counts: dict[str, int] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _required_numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise ValueError(f"Segment dataset is missing required column: {column}.")
    return pd.to_numeric(frame[column], errors="coerce")


def _non_monotonic_mask(frame: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=frame.index)
    if {"actual_segment_start_unix", "actual_segment_end_unix"}.issubset(frame.columns):
        starts = pd.to_numeric(frame["actual_segment_start_unix"], errors="coerce")
        ends = pd.to_numeric(frame["actual_segment_end_unix"], errors="coerce")
        mask |= starts.isna() | ends.isna() | (ends <= starts)

        if "trip_id" in frame.columns:
            trip_instance_columns = [
                column
                for column in ("source", "service_date", "trip_id", "vehicle_id")
                if column in frame.columns
            ]
            ordering_columns = list(trip_instance_columns)
            if "stop_sequence" in frame.columns:
                ordering_columns.append("stop_sequence")
            ordering_columns.append("_start")
            ordered = frame.assign(_start=starts, _end=ends).sort_values(ordering_columns)
            previous_end = ordered.groupby(
                trip_instance_columns,
                sort=False,
                dropna=False,
            )["_end"].shift(1)
            overlap = previous_end.notna() & (ordered["_start"] < previous_end)
            mask.loc[ordered.index] |= overlap
    return mask


def validate_segment_frame(
    dataframe: pd.DataFrame,
    *,
    source: str,
    thresholds: SegmentQualityThresholds | None = None,
) -> tuple[pd.DataFrame, SegmentQualityReport]:
    thresholds = thresholds or SegmentQualityThresholds()
    frame = dataframe.copy()
    actual = _required_numeric(frame, "actual_segment_minutes")
    scheduled = _required_numeric(frame, "scheduled_segment_minutes")
    distance = _required_numeric(frame, "distance_to_prev_stop_km")

    slowdown_ratio = actual / scheduled.replace(0.0, np.nan)
    speed_kph = distance / (actual / 60.0).replace(0.0, np.nan)

    rejection_masks: dict[str, pd.Series] = {
        "missing_or_non_numeric": actual.isna() | scheduled.isna() | distance.isna(),
        "nonpositive_actual_minutes": actual <= thresholds.min_actual_minutes,
        "nonpositive_scheduled_minutes": scheduled <= thresholds.min_scheduled_minutes,
        "actual_minutes_above_limit": actual > thresholds.max_actual_minutes,
        "slowdown_ratio_below_limit": slowdown_ratio < thresholds.min_slowdown_ratio,
        "slowdown_ratio_above_limit": slowdown_ratio > thresholds.max_slowdown_ratio,
        "speed_above_limit": (
            (distance >= thresholds.min_speed_check_distance_km)
            & (speed_kph > thresholds.max_speed_kph)
        ),
        "non_monotonic_timestamps": _non_monotonic_mask(frame),
    }

    if source == "realtime":
        if "reconstruction_confidence_score" not in frame.columns:
            rejection_masks["missing_reconstruction_confidence"] = pd.Series(
                True, index=frame.index
            )
        else:
            confidence = pd.to_numeric(
                frame["reconstruction_confidence_score"], errors="coerce"
            )
            rejection_masks["low_reconstruction_confidence"] = (
                confidence.isna() | (confidence < thresholds.min_realtime_confidence)
            )
        if "supervised_training_eligible" in frame.columns:
            eligible = frame["supervised_training_eligible"].fillna(False).eq(True)
            rejection_masks["not_supervised_training_eligible"] = ~eligible

    rejected = pd.Series(False, index=frame.index)
    rejection_counts: dict[str, int] = {}
    for reason, reason_mask in rejection_masks.items():
        normalized_mask = reason_mask.fillna(True)
        rejection_counts[reason] = int(normalized_mask.sum())
        rejected |= normalized_mask

    valid = frame.loc[~rejected].copy()
    valid["actual_segment_minutes"] = actual.loc[valid.index].astype("float32")
    valid["scheduled_segment_minutes"] = scheduled.loc[valid.index].astype("float32")
    valid["distance_to_prev_stop_km"] = distance.loc[valid.index].astype("float32")
    valid["slowdown_ratio"] = slowdown_ratio.loc[valid.index].astype("float32")
    valid["log_slowdown_ratio"] = np.log(valid["slowdown_ratio"]).astype("float32")

    report = SegmentQualityReport(
        input_rows=int(len(frame)),
        accepted_rows=int(len(valid)),
        rejected_rows=int(rejected.sum()),
        rejection_counts=rejection_counts,
        thresholds=thresholds.to_dict(),
    )
    return valid.reset_index(drop=True), report
