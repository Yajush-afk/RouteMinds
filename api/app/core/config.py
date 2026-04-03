from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "RouteMinds API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    MODEL_PATH: str = "artifacts/models/xgboost_segment_travel_time_model.joblib"
    SCHEMA_PATH: str = "artifacts/models/xgboost_segment_travel_time_schema.json"
    GTFS_STATIC_DIR: str = "data/raw"
    GTFS_RT_VEHICLE_POSITIONS_URL: str = "https://otd.delhi.gov.in/api/realtime/VehiclePositions.pb"
    GTFS_RT_API_KEY: str = ""
    GTFS_RT_AUTH_MODE: str = "auto"
    GTFS_RT_API_KEY_QUERY_PARAM: str = "key"
    GTFS_RT_RESPONSE_FORMAT: str = "auto"
    GTFS_RT_REFRESH_INTERVAL_SECONDS: int = 60
    GTFS_RT_CACHE_MAX_AGE_SECONDS: int = 300
    GTFS_RT_SNAPSHOT_PATH: str = ""

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return value

    @field_validator("GTFS_RT_AUTH_MODE", mode="before")
    @classmethod
    def parse_gtfs_rt_auth_mode(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"auto", "headers", "query"}:
                return normalized
        return value

    @field_validator("GTFS_RT_RESPONSE_FORMAT", mode="before")
    @classmethod
    def parse_gtfs_rt_response_format(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"auto", "json", "protobuf"}:
                return normalized
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
