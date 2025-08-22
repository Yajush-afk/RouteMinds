from pydantic import BaseModel, Field

class DelayRequest(BaseModel):

    route_short_name: str = Field(..., description="Human route ID (e.g., 534A)")
    stop_sequence: int = Field(..., ge=0)
    day_of_week: int = Field(..., ge=0, le=6) 
    hour_of_day: int = Field(..., ge=0, le=23)
    holiday_flag: int = Field(..., ge=0, le=1)     
    stop_lat: float = Field(..., description="Latitude of stop")
    stop_lon: float = Field(..., description="Longitude of stop")

class DelayResponse(BaseModel):
    predicted_delay: float = Field(..., description="Predicted delay in minutes (positive = late, negative = early)")
    model: str | None = Field(None, description="Model name used for prediction")
