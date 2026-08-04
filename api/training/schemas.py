from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


ML_V2_SCHEMA_VERSION = "2.0.0"

CANONICAL_SEGMENT_COLUMNS = (
    "service_date",
    "source",
    "trip_id",
    "route_id",
    "from_stop_id",
    "to_stop_id",
    "stop_sequence",
    "normalized_stop_position",
    "scheduled_segment_minutes",
    "actual_segment_minutes",
    "slowdown_ratio",
    "log_slowdown_ratio",
    "distance_to_prev_stop_km",
    "segment_start_scheduled_unix",
    "reconstruction_confidence_score",
    "sample_weight",
)

LIVE_FEATURE_COLUMNS = (
    "prev_segment_delay",
    "rolling_segment_delay_3",
    "route_delay_minutes_live",
    "segment_slowdown_index",
    "corridor_slowdown_score_live",
    "headway_irregularity_score_live",
    "bunching_indicator",
    "live_context_age_seconds",
    "live_context_observation_count",
    "live_context_available",
)


@dataclass(frozen=True, slots=True)
class SegmentQualityThresholds:
    min_actual_minutes: float = 0.0
    max_actual_minutes: float = 120.0
    min_scheduled_minutes: float = 0.0
    min_slowdown_ratio: float = 0.2
    max_slowdown_ratio: float = 5.0
    max_speed_kph: float = 80.0
    min_speed_check_distance_km: float = 0.05
    min_realtime_confidence: float = 0.7

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SegmentDatasetBuildOptions:
    source: str
    synthetic_sample_weight: float = 0.25
    realtime_sample_weight: float = 1.0
