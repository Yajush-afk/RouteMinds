from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class SegmentFeatureRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route_id: str | int
    from_stop_id: str | int
    to_stop_id: str | int
    stop_sequence: int
    normalized_stop_position: float
    distance_to_prev_stop_km: float
    segment_start_scheduled_unix: int
    scheduled_segment_minutes: float
    prev_segment_delay: float
    rolling_segment_delay_3: float
    route_delay_minutes_live: float = 0.0
    segment_slowdown_index: float = Field(default=1.0, ge=0.0)
    corridor_slowdown_score_live: float = Field(default=1.0, ge=0.0)
    headway_irregularity_score_live: float = Field(default=0.0, ge=0.0)
    bunching_indicator: float = Field(default=0.0, ge=0.0)
    live_context_age_seconds: float = Field(default=0.0, ge=0.0)
    live_context_observation_count: float = Field(default=0.0, ge=0.0)
    live_context_available: float = Field(default=0.0, ge=0.0, le=1.0)
    reconstruction_confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class SegmentPrediction(BaseModel):
    predicted_actual_segment_minutes: float
    predicted_segment_delay_minutes: float
    segment_uncertainty: float = Field(ge=0.0)
    segment_reliability_score: float = Field(ge=0.0, le=1.0)
    congestion_proxy_ratio: float = Field(ge=0.0)
    congestion_proxy_percent: float
    predicted_eta_lower_minutes: float = Field(ge=0.0)
    predicted_eta_upper_minutes: float = Field(ge=0.0)
    prediction_source: Literal["ml", "scheduled_fallback"] = "ml"
    model_supported: bool = True
    model_version: str = "legacy-v1"
    live_context_used: bool = False
    feature_quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    prediction_interval_method: Literal["xgboost_quantile", "fallback"] = "fallback"


class SegmentPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[SegmentFeatureRecord] = Field(min_length=1)


class SegmentPredictionResponse(BaseModel):
    predictions: list[SegmentPrediction]
