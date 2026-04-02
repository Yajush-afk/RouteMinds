from __future__ import annotations

from pydantic import BaseModel


class RealtimeRefreshResponse(BaseModel):
    fetched_snapshots: int
    enriched_segments: int
    latest_snapshot_time: int | None


class RealtimeStatusResponse(BaseModel):
    configured: bool
    last_refresh_time: int | None
    latest_snapshot_time: int | None
    cached_segments: int
    cached_vehicles: int
