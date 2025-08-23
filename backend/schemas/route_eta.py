from pydantic import BaseModel, Field
from typing import List, Optional, Tuple

Coord = Tuple[float, float]


class RouteEtaRequest(BaseModel):
    route_short_name: str = Field(..., description="Route short name (e.g., 142)")
    from_stop_id: Optional[int] = Field(None, description="GTFS stop_id for origin (preferred)")
    to_stop_id: Optional[int] = Field(None, description="GTFS stop_id for destination (preferred)")
    from_coord: Optional[Coord] = Field(None, description="Fallback origin coord (lat, lon)")
    to_coord: Optional[Coord] = Field(None, description="Fallback destination coord (lat, lon)")
    timestamp_iso: Optional[str] = Field(None, description="ISO timestamp for journey start (tz aware preferred)")
    holiday_flag: int = Field(0, ge=0, le=1, description="1 if holiday else 0")


class StopPrediction(BaseModel):
    stop_id: int
    stop_name: Optional[str]
    stop_sequence: int
    lat: float
    lon: float
    scheduled_arrival_time: Optional[str]
    predicted_delay_minutes: float
    predicted_eta_iso: str


class RouteEtaResponse(BaseModel):
    route_short_name: str
    waypoints: List[Coord]  # list of (lat, lon)
    stops: List[StopPrediction]
    summary: dict
