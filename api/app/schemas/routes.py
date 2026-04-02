from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RouteOptimizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_stop_id: str | int
    destination_stop_id: str | int
    query_timestamp_unix: int


class RouteStop(BaseModel):
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float


class RouteSegmentPrediction(BaseModel):
    route_id: str
    from_stop_id: str
    to_stop_id: str
    stop_sequence: int
    normalized_stop_position: float
    distance_to_prev_stop_km: float
    scheduled_segment_minutes: float
    predicted_actual_segment_minutes: float
    predicted_segment_delay_minutes: float


class RouteOptimizationResponse(BaseModel):
    stops: list[RouteStop]
    segments: list[RouteSegmentPrediction]
    total_predicted_eta_minutes: float = Field(ge=0.0)
