from __future__ import annotations

from pydantic import BaseModel


class RealtimeRefreshResponse(BaseModel):
    fetched_snapshots: int
    enriched_segments: int
    latest_snapshot_time: int | None
    unmatched_snapshots: int
    unmatched_trips: int
    unmatched_vehicles: int
    malformed_records: int
    provider_format: str | None
    auth_mode: str
    last_refresh_successful: bool
    last_refresh_error: str | None


class RealtimeStatusResponse(BaseModel):
    configured: bool
    last_refresh_time: int | None
    last_successful_refresh_time: int | None
    latest_snapshot_time: int | None
    fetched_snapshots: int
    enriched_segments: int
    unmatched_snapshots: int
    unmatched_trips: int
    unmatched_vehicles: int
    malformed_records: int
    cached_segments: int
    cached_vehicles: int
    cache_max_age_seconds: int
    cache_is_fresh: bool
    provider_format: str | None
    auth_mode: str
    last_refresh_successful: bool
    last_refresh_error: str | None
