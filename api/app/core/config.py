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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
