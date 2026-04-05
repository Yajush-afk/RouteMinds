from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parents[3]

def normalize_auth0_domain(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("https://"):
        normalized = normalized[len("https://") :]
    return normalized.rstrip("/")


def normalize_comma_separated_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def normalize_origin(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "CORS_ALLOW_ORIGINS must contain only http or https origins."
        )
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError(
            "CORS_ALLOW_ORIGINS entries must be bare origins without paths, queries, or fragments."
        )
    return f"{parsed.scheme}://{parsed.netloc}"


def normalize_auth0_issuer(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("AUTH0_ISSUER must be a valid https URL.")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError(
            "AUTH0_ISSUER must point to the tenant root and cannot include paths, queries, or fragments."
        )
    return f"https://{parsed.netloc}/"

class Settings(BaseSettings):
    APP_NAME: str = "RouteMinds API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CORS_ALLOW_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "http://localhost:5173,"
        "http://127.0.0.1:5173"
    )
    AUTH0_ENABLED: bool = False
    AUTH0_DOMAIN: str = ""
    AUTH0_AUDIENCE: str = ""
    AUTH0_ISSUER: str = ""
    AUTH0_ALGORITHMS: str = "RS256"
    AUTH0_REALTIME_REQUIRED_PERMISSION: str = "realtime:manage"

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

    @field_validator("AUTH0_ENABLED", mode="before")
    @classmethod
    def parse_auth0_enabled(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "enabled"}:
                return True
            if normalized in {"0", "false", "no", "off", "disabled"}:
                return False
        return value

    @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value):
        if isinstance(value, str):
            origins = [normalize_origin(origin) for origin in normalize_comma_separated_values(value)]
            if not origins:
                raise ValueError("CORS_ALLOW_ORIGINS must contain at least one origin.")
            return ",".join(origins)
        return value

    @field_validator("AUTH0_DOMAIN", mode="before")
    @classmethod
    def parse_auth0_domain(cls, value):
        if isinstance(value, str):
            return normalize_auth0_domain(value)
        return value

    @field_validator("AUTH0_AUDIENCE", "AUTH0_REALTIME_REQUIRED_PERMISSION", mode="before")
    @classmethod
    def strip_string_settings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("AUTH0_ISSUER", mode="before")
    @classmethod
    def parse_auth0_issuer(cls, value):
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return ""
            return normalize_auth0_issuer(normalized)
        return value

    @field_validator("AUTH0_ALGORITHMS", mode="before")
    @classmethod
    def parse_auth0_algorithms(cls, value):
        if isinstance(value, str):
            algorithms = [
                algorithm.strip().upper()
                for algorithm in value.split(",")
                if algorithm.strip()
            ]
            if not algorithms:
                raise ValueError("AUTH0_ALGORITHMS must contain at least one algorithm.")
            return ",".join(algorithms)
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

    def validate_runtime_configuration(self) -> None:
        if not self.AUTH0_ENABLED:
            return

        missing_settings: list[str] = []
        if not self.AUTH0_DOMAIN:
            missing_settings.append("AUTH0_DOMAIN")
        if not self.AUTH0_AUDIENCE:
            missing_settings.append("AUTH0_AUDIENCE")
        if not self.AUTH0_REALTIME_REQUIRED_PERMISSION:
            missing_settings.append("AUTH0_REALTIME_REQUIRED_PERMISSION")

        if missing_settings:
            raise ValueError(
                "Auth0 is enabled but the following settings are missing: "
                + ", ".join(missing_settings)
                + "."
            )

        if self.AUTH0_ISSUER:
            issuer_host = urlparse(self.AUTH0_ISSUER).netloc
            if issuer_host != self.AUTH0_DOMAIN:
                raise ValueError(
                    "AUTH0_ISSUER host must match AUTH0_DOMAIN so token issuer and JWKS lookup use the same tenant."
                )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
