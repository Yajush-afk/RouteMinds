import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.api.v1.auth import router as auth_router
from api.app.api.v1.health import router as health_router
from api.app.api.v1.predictions import router as predictions_router
from api.app.api.v1.realtime import router as realtime_router
from api.app.api.v1.routes import router as routes_router
from api.app.api.v1.stops import router as stops_router
from api.app.core.config import settings
from api.app.core.exceptions import RouteMindsException, routeminds_exception_handler
from api.app.services.gtfs_graph_service import GTFSGraphService
from api.app.services.realtime_enrichment_service import get_realtime_enrichment_service

logger = logging.getLogger(__name__)


def parse_cors_allow_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


async def realtime_refresh_loop() -> None:
    interval_seconds = settings.GTFS_RT_REFRESH_INTERVAL_SECONDS
    if interval_seconds <= 0:
        return

    while True:
        try:
            service = get_realtime_enrichment_service()
            if service.get_status()["configured"]:
                await asyncio.to_thread(service.refresh_vehicle_positions)
        except Exception as exc:
            logger.warning("Background GTFS-RT refresh failed: %s", exc)
        await asyncio.sleep(interval_seconds)


async def warm_static_graph() -> None:
    try:
        await asyncio.to_thread(
            GTFSGraphService(settings.GTFS_STATIC_DIR).get_graph
        )
    except Exception as exc:
        logger.warning("Static graph warm-up failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime_configuration()
    if not settings.auth_enabled:
        logger.warning(
            "Supabase auth is disabled. Protected API routes are open; use this only for local development."
        )
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    graph_warmup_task = asyncio.create_task(warm_static_graph())
    refresh_task = asyncio.create_task(realtime_refresh_loop())
    try:
        yield
    finally:
        graph_warmup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await graph_warmup_task
        refresh_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await refresh_task
        print("Shutting down RouteMinds API")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered intelligent transit routing and delay prediction for Delhi bus routes.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_allow_origins(settings.CORS_ALLOW_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RouteMindsException, routeminds_exception_handler)

API_V1_PREFIX = "/api/v1"


def include_api_routes(prefix: str = "") -> None:
    app.include_router(auth_router, prefix=prefix)
    app.include_router(health_router, prefix=prefix)
    app.include_router(stops_router, prefix=prefix)
    app.include_router(routes_router, prefix=prefix)
    app.include_router(predictions_router, prefix=prefix)
    app.include_router(realtime_router, prefix=prefix)


include_api_routes()
include_api_routes(API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
