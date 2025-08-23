# services/eta.py
from __future__ import annotations

from typing import List, Tuple, Optional
import os
from datetime import datetime, date, time, timedelta

import numpy as np
import pandas as pd

from schemas.route_eta import RouteEtaRequest, RouteEtaResponse, StopPrediction

Coord = Tuple[float, float]


class ETAService:
    """
    Simple ETA service based on historical mean delay per stop/time slice.

    - Filters the dataset by route (route_short_name OR route_id == provided string).
    - Optionally slices between from_stop_id and to_stop_id using stop_sequence order.
    - Computes mean delay per (stop_id, day_of_week, hour_of_day) with fallbacks.
    - Builds waypoints (lat, lon) and per-stop ETA timeline.
    """

    def __init__(self, dataset_path: str):
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset not found at: {dataset_path}")

        df = pd.read_csv(dataset_path)

        required = {
            "trip_id",
            "route_id",
            "route_short_name",
            "stop_id",
            "stop_name",
            "stop_lat",
            "stop_lon",
            "stop_sequence",
            "scheduled_arrival_time",
            "day_of_week",
            "hour_of_day",
            "holiday_flag",
            "delay_minutes",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Dataset is missing columns: {missing}")

        # Normalize types
        df["route_id"] = df["route_id"].astype(str)
        df["route_short_name"] = df["route_short_name"].astype(str)

        # stop_id & stop_sequence sometimes read as float; coerce to Int64
        df["stop_id"] = pd.to_numeric(df["stop_id"], errors="coerce").astype("Int64")
        df["stop_sequence"] = pd.to_numeric(df["stop_sequence"], errors="coerce").astype("Int64")

        # lat/lon numeric
        df["stop_lat"] = pd.to_numeric(df["stop_lat"], errors="coerce")
        df["stop_lon"] = pd.to_numeric(df["stop_lon"], errors="coerce")

        # times as strings "HH:MM:SS"
        df["scheduled_arrival_time"] = df["scheduled_arrival_time"].astype(str)

        # basic cleanup: drop rows we cannot use
        df = df.dropna(subset=["stop_id", "stop_sequence", "stop_lat", "stop_lon"])

        self.df = df.reset_index(drop=True)

        # Precompute aggregates for fast lookup
        self.delay_by_stop_dow_hour = (
            self.df.groupby(["route_id", "route_short_name", "stop_id", "day_of_week", "hour_of_day"])["delay_minutes"]
            .mean()
            .to_dict()
        )
        self.delay_by_stop = (
            self.df.groupby(["route_id", "route_short_name", "stop_id"])["delay_minutes"]
            .mean()
            .to_dict()
        )
        self.delay_by_route = (
            self.df.groupby(["route_id", "route_short_name"])["delay_minutes"]
            .mean()
            .to_dict()
        )
        self.overall_mean_delay = float(self.df["delay_minutes"].mean())

    @staticmethod
    def _parse_iso(ts: Optional[str]) -> datetime:
        if not ts:
            return datetime.now()
        # Robust ISO parsing without extra dependencies
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return datetime.now()

    @staticmethod
    def _parse_hms(hms: str) -> time:
        try:
            parts = [int(p) for p in hms.split(":")]
            if len(parts) == 3:
                return time(parts[0], parts[1], parts[2])
            if len(parts) == 2:
                return time(parts[0], parts[1], 0)
            return time(0, 0, 0)
        except Exception:
            return time(0, 0, 0)

    def _filter_route_df(self, route_key: str) -> pd.DataFrame:
        route_key = str(route_key).strip()
        df = self.df
        # Match either by route_short_name or by route_id (helps if dataset uses one or the other)
        mask = (df["route_short_name"] == route_key) | (df["route_id"] == route_key)
        route_df = df.loc[mask].copy()
        if route_df.empty:
            raise ValueError(f"No rows found for route '{route_key}' in either route_short_name or route_id.")
        return route_df

    def _slice_stops(
        self,
        route_df: pd.DataFrame,
        from_stop_id: Optional[int],
        to_stop_id: Optional[int]
    ) -> pd.DataFrame:
        # Use the first trip’s ordering if multiple trips exist; ordering is via stop_sequence
        ordered = route_df.sort_values(["stop_sequence", "scheduled_arrival_time"]).copy()

        if from_stop_id is None and to_stop_id is None:
            return ordered

        # Find sequences for given stop IDs
        def first_seq(sid: int) -> Optional[int]:
            ser = ordered.loc[ordered["stop_id"] == sid, "stop_sequence"]
            return int(ser.iloc[0]) if not ser.empty else None

        start_seq = first_seq(from_stop_id) if from_stop_id is not None else None
        end_seq = first_seq(to_stop_id) if to_stop_id is not None else None

        if start_seq is None and from_stop_id is not None:
            # fallback: just return full ordered; frontend can still draw
            return ordered
        if end_seq is None and to_stop_id is not None:
            return ordered

        if start_seq is not None and end_seq is not None:
            if start_seq <= end_seq:
                sl = ordered[(ordered["stop_sequence"] >= start_seq) & (ordered["stop_sequence"] <= end_seq)].copy()
            else:
                sl = ordered[(ordered["stop_sequence"] >= end_seq) & (ordered["stop_sequence"] <= start_seq)].copy()
            return sl if not sl.empty else ordered

        # If only one bound is provided, keep from that bound to the end (or start)
        if start_seq is not None:
            sl = ordered[ordered["stop_sequence"] >= start_seq].copy()
            return sl if not sl.empty else ordered

        if end_seq is not None:
            sl = ordered[ordered["stop_sequence"] <= end_seq].copy()
            return sl if not sl.empty else ordered

        return ordered

    def _mean_delay_for_stop(self, route_id: str, route_short_name: str, stop_id: int, dow: int, hour: int) -> float:
        # 1) exact (route_id, route_short_name, stop_id, dow, hour)
        key = (route_id, route_short_name, stop_id, dow, hour)
        v = self.delay_by_stop_dow_hour.get(key, np.nan)
        if pd.notna(v):
            return float(v)
        # 2) by stop
        key2 = (route_id, route_short_name, stop_id)
        v2 = self.delay_by_stop.get(key2, np.nan)
        if pd.notna(v2):
            return float(v2)
        # 3) by route
        key3 = (route_id, route_short_name)
        v3 = self.delay_by_route.get(key3, np.nan)
        if pd.notna(v3):
            return float(v3)
        # 4) overall
        return float(self.overall_mean_delay)

    def get_eta(self, request: RouteEtaRequest) -> RouteEtaResponse:
        # Base time context
        base_dt = self._parse_iso(request.timestamp_iso)
        base_date = date(year=base_dt.year, month=base_dt.month, day=base_dt.day)
        dow = base_dt.weekday()  # 0=Mon
        hour = base_dt.hour

        # Filter route
        route_df = self._filter_route_df(request.route_short_name)

        # Distill a single (route_id, route_short_name) representative (there may be multiple; take the most frequent)
        repr_route = (
            route_df.groupby(["route_id", "route_short_name"])["stop_id"]
            .count()
            .sort_values(ascending=False)
            .index[0]
        )
        repr_route_id, repr_route_short = repr_route

        # Slice between stop ids if provided
        sliced = self._slice_stops(route_df, request.from_stop_id, request.to_stop_id)
        # Collapse to unique stops in order
        stops_df = (
            sliced.sort_values(["stop_sequence", "scheduled_arrival_time"])
            .groupby("stop_id", as_index=False)
            .first()
            .sort_values("stop_sequence")
            .reset_index(drop=True)
        )

        waypoints: List[Coord] = []
        stops_out: List[StopPrediction] = []

        total_delay = 0.0
        for _, row in stops_df.iterrows():
            sid = int(row["stop_id"])
            lat = float(row["stop_lat"])
            lon = float(row["stop_lon"])
            sname = (row["stop_name"] if pd.notna(row["stop_name"]) else None)
            seq = int(row["stop_sequence"])

            # pick the stored scheduled_arrival_time string
            sched_str = str(row["scheduled_arrival_time"])
            sched_time = self._parse_hms(sched_str)
            sched_dt = datetime.combine(base_date, sched_time)

            # predicted delay (minutes)
            dmin = self._mean_delay_for_stop(
                repr_route_id, repr_route_short, sid, dow, hour
            )
            # prevent weird negatives if your dataset has early arrivals
            dmin_rounded = float(round(max(dmin, 0.0), 2))
            total_delay += dmin_rounded

            eta_dt = sched_dt + timedelta(minutes=dmin_rounded)

            waypoints.append((lat, lon))
            stops_out.append(
                StopPrediction(
                    stop_id=sid,
                    stop_name=sname,
                    stop_sequence=seq,
                    lat=lat,
                    lon=lon,
                    scheduled_arrival_time=sched_str,
                    predicted_delay_minutes=dmin_rounded,
                    predicted_eta_iso=eta_dt.isoformat(),
                )
            )

        summary = {
            "n_stops": len(stops_out),
            "start_stop_id": int(stops_out[0].stop_id) if stops_out else None,
            "end_stop_id": int(stops_out[-1].stop_id) if stops_out else None,
            "total_predicted_delay_minutes": float(round(total_delay, 2)),
            "route_key_used": request.route_short_name,
            "repr_route_id": repr_route_id,
            "repr_route_short_name": repr_route_short,
            "context_day_of_week": dow,
            "context_hour_of_day": hour,
        }

        return RouteEtaResponse(
            route_short_name=request.route_short_name,
            waypoints=waypoints,
            stops=stops_out,
            summary=summary,
        )
