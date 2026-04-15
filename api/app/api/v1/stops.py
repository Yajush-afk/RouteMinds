from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.app.core.auth import require_auth
from api.app.core.config import settings
from api.app.schemas.stops import NearbyStopsResponse, StopSearchResponse
from api.app.services.gtfs_graph_service import GTFSGraphService

router = APIRouter(prefix="/stops", tags=["Stops"])


def get_gtfs_graph_service() -> GTFSGraphService:
    return GTFSGraphService(settings.GTFS_STATIC_DIR)


@router.get("/nearby", response_model=NearbyStopsResponse)
async def get_nearby_stops(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
    limit: int = Query(5, ge=1, le=20),
    _claims: dict = Depends(require_auth),
) -> NearbyStopsResponse:
    graph_service = get_gtfs_graph_service()
    return NearbyStopsResponse(
        stops=graph_service.get_nearest_stops(lat, lon, limit=limit)
    )


@router.get("/search", response_model=StopSearchResponse)
async def search_stops(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(8, ge=1, le=20),
) -> StopSearchResponse:
    graph_service = get_gtfs_graph_service()
    return StopSearchResponse(stops=graph_service.search_stops(q, limit=limit))
