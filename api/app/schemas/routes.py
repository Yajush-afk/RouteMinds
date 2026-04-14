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
    is_transfer: bool = False
    transfer_buffer_minutes: float = Field(default=0.0, ge=0.0)
    transfer_slack_minutes: float = Field(default=0.0, ge=0.0)
    transfer_wait_uncertainty_minutes: float = Field(default=0.0, ge=0.0)
    missed_transfer_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    is_fragile_transfer: bool = False
    travel_time_cost: float = Field(ge=0.0)
    waiting_time_cost: float = Field(ge=0.0)
    transfer_penalty_cost: float = Field(ge=0.0)
    uncertainty_penalty_cost: float = Field(ge=0.0)
    reliability_penalty_cost: float = Field(ge=0.0)
    unstable_corridor_penalty_cost: float = Field(ge=0.0)
    detour_penalty_cost: float = Field(ge=0.0)
    fragile_transfer_penalty_cost: float = Field(ge=0.0)
    generalized_cost: float = Field(ge=0.0)
    congestion_proxy_ratio: float = Field(ge=0.0)
    congestion_proxy_percent: float
    corridor_instability_score_live: float = Field(ge=0.0, le=1.0)
    service_quality_score: float = Field(ge=0.0, le=1.0)
    predicted_actual_segment_minutes: float
    predicted_segment_delay_minutes: float
    segment_uncertainty: float = Field(ge=0.0)
    segment_reliability_score: float = Field(ge=0.0, le=1.0)
    predicted_eta_lower_minutes: float = Field(ge=0.0)
    predicted_eta_upper_minutes: float = Field(ge=0.0)


class RouteCostBreakdown(BaseModel):
    travel_time_cost: float = Field(ge=0.0)
    waiting_time_cost: float = Field(ge=0.0)
    transfer_penalty_cost: float = Field(ge=0.0)
    uncertainty_penalty_cost: float = Field(ge=0.0)
    reliability_penalty_cost: float = Field(ge=0.0)
    unstable_corridor_penalty_cost: float = Field(ge=0.0)
    detour_penalty_cost: float = Field(ge=0.0)
    fragile_transfer_penalty_cost: float = Field(ge=0.0)
    generalized_cost: float = Field(ge=0.0)


class RouteAlternativeSummary(BaseModel):
    label: str
    total_predicted_eta_minutes: float = Field(ge=0.0)
    route_reliability_score: float = Field(ge=0.0, le=1.0)
    generalized_cost_minutes: float = Field(ge=0.0)


class RouteOptimizationResponse(BaseModel):
    stops: list[RouteStop]
    segments: list[RouteSegmentPrediction]
    total_predicted_eta_minutes: float = Field(ge=0.0)
    predicted_eta_lower_minutes: float = Field(ge=0.0)
    predicted_eta_upper_minutes: float = Field(ge=0.0)
    route_reliability_score: float = Field(ge=0.0, le=1.0)
    generalized_cost_minutes: float = Field(ge=0.0)
    total_wait_minutes: float = Field(ge=0.0)
    total_in_vehicle_minutes: float = Field(ge=0.0)
    transfer_count: int = Field(ge=0)
    fragile_transfer_count: int = Field(ge=0)
    transfer_fragility_score: float = Field(ge=0.0, le=1.0)
    congestion_proxy_ratio: float = Field(ge=0.0)
    congestion_proxy_percent: float
    service_quality_score: float = Field(ge=0.0, le=1.0)
    selection_reasons: list[str]
    explanation_summary: str
    cost_breakdown: RouteCostBreakdown
    alternatives: list[RouteAlternativeSummary] = Field(default_factory=list)
