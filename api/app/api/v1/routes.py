from fastapi import APIRouter

from api.app.core.config import settings
from api.app.schemas.routes import (
    RouteOptimizationRequest,
    RouteOptimizationResponse,
)
from api.app.services.gtfs_graph_service import GTFSGraphService
from api.app.services.prediction_service import PredictionService
from api.app.services.route_optimization_service import RouteOptimizationService

router = APIRouter(prefix="/routes", tags=["Routes"])


def get_route_optimization_service() -> RouteOptimizationService:
    graph_service = GTFSGraphService(settings.GTFS_STATIC_DIR)
    prediction_service = PredictionService(
        model_path=settings.MODEL_PATH,
        schema_path=settings.SCHEMA_PATH,
    )
    return RouteOptimizationService(graph_service, prediction_service)


@router.post("/optimize", response_model=RouteOptimizationResponse)
async def optimize_route(
    request: RouteOptimizationRequest,
) -> RouteOptimizationResponse:
    route_service = get_route_optimization_service()
    result = route_service.optimize_route(
        origin_stop_id=request.origin_stop_id,
        destination_stop_id=request.destination_stop_id,
        query_timestamp_unix=request.query_timestamp_unix,
    )
    return RouteOptimizationResponse(
        stops=result.stops,
        segments=result.segments,
        total_predicted_eta_minutes=result.total_predicted_eta_minutes,
    )
