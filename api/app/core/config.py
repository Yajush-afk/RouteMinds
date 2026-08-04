from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings

REPO_ROOT = Path(__file__).resolve().parents[3]

SUPPORTED_SUPABASE_JWT_ALGORITHMS = {
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "EdDSA",
}


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


def normalize_supabase_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("SUPABASE_URL must be a valid https origin.")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise ValueError(
            "SUPABASE_URL must be a bare project origin without paths, queries, or fragments."
        )
    return f"https://{parsed.netloc}"


def normalize_supabase_issuer(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("SUPABASE_JWT_ISSUER must be a valid https URL.")
    if parsed.params or parsed.query or parsed.fragment:
        raise ValueError(
            "SUPABASE_JWT_ISSUER cannot include params, queries, or fragments."
        )
    normalized_path = parsed.path.rstrip("/")
    if normalized_path != "/auth/v1":
        raise ValueError(
            "SUPABASE_JWT_ISSUER must point to the project auth issuer at /auth/v1."
        )
    return f"https://{parsed.netloc}{normalized_path}"


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
    SUPABASE_AUTH_ENABLED: bool = False
    SUPABASE_URL: str = ""
    SUPABASE_JWT_ISSUER: str = ""
    SUPABASE_JWT_AUDIENCE: str = ""
    SUPABASE_JWT_ALGORITHMS: str = "ES256,RS256"
    SUPABASE_REALTIME_REQUIRED_PERMISSION: str = "realtime:manage"

    MODEL_PATH: str = "artifacts/models/xgboost_segment_travel_time_model.joblib"
    SCHEMA_PATH: str = "artifacts/models/xgboost_segment_travel_time_schema.json"
    MODEL_V2_MANIFEST_PATH: str = ""
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

    @field_validator("SUPABASE_AUTH_ENABLED", mode="before")
    @classmethod
    def parse_supabase_auth_enabled(cls, value):
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
            origins = [
                normalize_origin(origin)
                for origin in normalize_comma_separated_values(value)
            ]
            if not origins:
                raise ValueError("CORS_ALLOW_ORIGINS must contain at least one origin.")
            return ",".join(origins)
        return value

    @field_validator("SUPABASE_URL", mode="before")
    @classmethod
    def parse_supabase_url(cls, value):
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return ""
            return normalize_supabase_url(normalized)
        return value

    @field_validator(
        "SUPABASE_JWT_AUDIENCE",
        "SUPABASE_REALTIME_REQUIRED_PERMISSION",
        mode="before",
    )
    @classmethod
    def strip_string_settings(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("SUPABASE_JWT_ISSUER", mode="before")
    @classmethod
    def parse_supabase_jwt_issuer(cls, value):
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return ""
            return normalize_supabase_issuer(normalized)
        return value

    @field_validator("SUPABASE_JWT_ALGORITHMS", mode="before")
    @classmethod
    def parse_supabase_jwt_algorithms(cls, value):
        if isinstance(value, str):
            algorithms = [
                algorithm.strip().upper()
                for algorithm in value.split(",")
                if algorithm.strip()
            ]
            if not algorithms:
                raise ValueError(
                    "SUPABASE_JWT_ALGORITHMS must contain at least one algorithm."
                )
            unsupported_algorithms = [
                algorithm
                for algorithm in algorithms
                if algorithm not in SUPPORTED_SUPABASE_JWT_ALGORITHMS
            ]
            if unsupported_algorithms:
                raise ValueError(
                    "SUPABASE_JWT_ALGORITHMS must use JWKS-compatible asymmetric algorithms only: "
                    + ", ".join(sorted(SUPPORTED_SUPABASE_JWT_ALGORITHMS))
                    + "."
                )
            return ",".join(algorithms)
        return value

    @property
    def auth_enabled(self) -> bool:
        return self.SUPABASE_AUTH_ENABLED

    @property
    def auth_project_url(self) -> str:
        return self.SUPABASE_URL

    @property
    def auth_jwt_issuer(self) -> str:
        if self.SUPABASE_JWT_ISSUER:
            return self.SUPABASE_JWT_ISSUER
        if self.auth_project_url:
            return f"{self.auth_project_url}/auth/v1"
        return ""

    @property
    def auth_jwt_audience(self) -> str:
        return self.SUPABASE_JWT_AUDIENCE

    @property
    def auth_jwt_algorithms(self) -> str:
        return self.SUPABASE_JWT_ALGORITHMS

    @property
    def realtime_required_permission(self) -> str:
        return self.SUPABASE_REALTIME_REQUIRED_PERMISSION

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
        if not self.auth_enabled:
            return

        missing_settings: list[str] = []
        if not self.auth_project_url:
            missing_settings.append("SUPABASE_URL")
        if not self.auth_jwt_audience:
            missing_settings.append("SUPABASE_JWT_AUDIENCE")
        if not self.realtime_required_permission:
            missing_settings.append("SUPABASE_REALTIME_REQUIRED_PERMISSION")

        if missing_settings:
            raise ValueError(
                "Supabase auth is enabled but the following settings are missing: "
                + ", ".join(missing_settings)
                + "."
            )

        issuer = self.auth_jwt_issuer
        if issuer:
            issuer_parts = urlparse(issuer)
            project_host = urlparse(self.auth_project_url).netloc
            if issuer_parts.netloc != project_host:
                raise ValueError(
                    "SUPABASE_JWT_ISSUER host must match SUPABASE_URL so token issuer and JWKS lookup use the same project."
                )
            if issuer_parts.path.rstrip("/") != "/auth/v1":
                raise ValueError(
                    "SUPABASE_JWT_ISSUER must point to the project auth issuer at /auth/v1."
                )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
