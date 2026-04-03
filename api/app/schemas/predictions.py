from __future__ import annotations
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


class SegmentPrediction(BaseModel):
    predicted_actual_segment_minutes: float
    predicted_segment_delay_minutes: float


class SegmentPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[SegmentFeatureRecord] = Field(min_length=1)


class SegmentPredictionResponse(BaseModel):
    predictions: list[SegmentPrediction]
