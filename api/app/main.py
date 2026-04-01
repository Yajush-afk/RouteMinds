from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.app.core.config import settings
from api.app.core.exceptions import RouteMindsException, routeminds_exception_handler
from api.app.api.v1.health import router as health_router
from api.app.api.v1.routes import router as routes_router
from api.app.api.v1.predictions import router as predictions_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    print("Shutting down RouteMinds API")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered intelligent transit routing and delay prediction for Delhi bus routes.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RouteMindsException, routeminds_exception_handler)

API_V1_PREFIX = "/api/v1"

app.include_router(health_router, prefix=API_V1_PREFIX)
app.include_router(routes_router, prefix=API_V1_PREFIX)
app.include_router(predictions_router, prefix=API_V1_PREFIX)

@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
