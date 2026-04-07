import asyncio

from fastapi import APIRouter

from api.app.schemas.realtime import RealtimeRefreshResponse, RealtimeStatusResponse
from api.app.services.realtime_enrichment_service import get_realtime_enrichment_service

router = APIRouter(
    prefix="/realtime",
    tags=["Realtime"],
)


@router.post("/refresh", response_model=RealtimeRefreshResponse)
async def refresh_realtime(
) -> RealtimeRefreshResponse:
    service = get_realtime_enrichment_service()
    result = await asyncio.to_thread(service.refresh_vehicle_positions)
    return RealtimeRefreshResponse(**result)


@router.get("/status", response_model=RealtimeStatusResponse)
async def realtime_status(
) -> RealtimeStatusResponse:
    service = get_realtime_enrichment_service()
    return RealtimeStatusResponse(**service.get_status())
