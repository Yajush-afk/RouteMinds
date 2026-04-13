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
    scheduled_departure_unix: int | None = None
    stop_sequence: int
    normalized_stop_position: float
    distance_to_prev_stop_km: float
    scheduled_segment_minutes: float
    scheduled_wait_minutes_before_boarding: float = Field(default=0.0, ge=0.0)
    wait_minutes_before_boarding: float = Field(default=0.0, ge=0.0)
    boarding_feasibility_score: float = Field(ge=0.0, le=1.0)
    predicted_actual_segment_minutes: float
    predicted_segment_delay_minutes: float
    segment_uncertainty: float = Field(ge=0.0)
    segment_reliability_score: float = Field(ge=0.0, le=1.0)
    predicted_eta_lower_minutes: float = Field(ge=0.0)
    predicted_eta_upper_minutes: float = Field(ge=0.0)


class RouteOptimizationResponse(BaseModel):
    stops: list[RouteStop]
    segments: list[RouteSegmentPrediction]
    total_predicted_eta_minutes: float = Field(ge=0.0)
    predicted_eta_lower_minutes: float = Field(ge=0.0)
    predicted_eta_upper_minutes: float = Field(ge=0.0)
    route_reliability_score: float = Field(ge=0.0, le=1.0)
