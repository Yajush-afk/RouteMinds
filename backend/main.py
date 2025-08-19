from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Dyanimic Route Rationalisation API",
    description="API backend for predicting optimal routes based on traffic conditions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) #replace * with frontend urls 

class RouteRequest(BaseModel):
    start_point: str
    end_point: str
    traffic_level: str
    weather:str

class RouteOptions(BaseModel):
    route_name: str
    estimated_time_minutes: int
    congestion_level: str

class RouteResponse(BaseModel):
    best_route: str
    alternatives: List[RouteOptions]

@app.get("/ping")
def health_check():
    return{"status":"Backend is working"}


