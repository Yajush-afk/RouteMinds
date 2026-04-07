from __future__ import annotations

from pydantic import BaseModel, Field


class NearbyStop(BaseModel):
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    distance_km: float = Field(ge=0.0)


class NearbyStopsResponse(BaseModel):
    stops: list[NearbyStop]
