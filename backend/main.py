from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Dynamic Route Rationalisation API",
    description="API backend for predicting optimal routes based on traffic conditions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RouteRequest(BaseModel):
    start_point: str
    end_point: str
    traffic_level: str
    weather: str

class RouteOptions(BaseModel):
    route_name: str
    estimated_time_minutes: int
    congestion_level: str

class RouteResponse(BaseModel):
    best_route: str
    alternatives: List[RouteOptions]

@app.get("/ping")
def health_check():
    return {"status": "Backend is working"}

@app.post("/predict", response_model=RouteResponse)
async def predict_route(request: RouteRequest):
    """
    Takes start_point, end_point, traffic_level, and weather as input,
    and returns the best route with alternatives.
    Currently returns dummy values — replace with ML model predictions later.
    """
    best_route = f"Optimal route from {request.start_point} to {request.end_point}"

    return RouteResponse(
        best_route=best_route,
        alternatives=[
            RouteOptions(
                route_name="Route A",
                estimated_time_minutes=20,
                congestion_level="Low"
            ),
            RouteOptions(
                route_name="Route B",
                estimated_time_minutes=25,
                congestion_level="Medium"
            ),
            RouteOptions(
                route_name="Route C",
                estimated_time_minutes=30,
                congestion_level="High"
            )
        ]
    )
