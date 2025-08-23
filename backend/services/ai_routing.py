# backend/services/ai_routing.py
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, List
import numpy as np

# your existing model wrapper
from models.prediction import PredictionModel

# utility helpers (these are your working utils)
from utils.route_index import get_stops_for_route, find_nearest_stop, slice_stops_by_ids
from utils.preprocessing import build_feature_vector

BASE = Path(__file__).resolve().parents[1]  # backend/
MODEL_P = BASE / "models" / "trained_model.pkl"
ENCODER_P = BASE / "models" / "route_label_encoder.pkl"
if not MODEL_P.exists():
    MODEL_P = BASE / "artifacts" / "trained_model.pkl"
if not ENCODER_P.exists():
    ENCODER_P = BASE / "artifacts" / "encoder.pkl"

# instantiate wrapper once
_model_wrapper = PredictionModel(str(MODEL_P), str(ENCODER_P))


class AIRoutingService:
    def __init__(self, model_wrapper: Optional[Any] = None, index_path: Optional[str] = None):
        # model_wrapper expected to be your PredictionModel instance
        self.model_wrapper: Any = model_wrapper or _model_wrapper
        self.index_path = index_path

    def compute_route_eta(self, req: Any) -> Any:
        """
        req is expected to be a schemas.route_eta.RouteEtaRequest Pydantic object,
        but we import schemas inside the function to avoid circular imports.
        """
        # local import to avoid circular import issues with routes -> services -> schemas
        from schemas.route_eta import RouteEtaRequest, RouteEtaResponse, StopPrediction  # type: ignore

        # Validate / cast if necessary (if passed dict)
        if not isinstance(req, RouteEtaRequest):
            # if someone passed a dict, coerce
            req = RouteEtaRequest.model_validate(req)  # pydantic v2; for v1 use RouteEtaRequest(**req) 

        route_name = req.route_short_name
        # 1) load stops for route
        route_stops = get_stops_for_route(route_name, self.index_path)

        # 2) determine slice
        if req.from_stop_id is not None and req.to_stop_id is not None:
            stops_slice = slice_stops_by_ids(route_stops, req.from_stop_id, req.to_stop_id)
        else:
            # fallback to nearest stops by coords
            if req.from_coord is None or req.to_coord is None:
                raise ValueError("Either from_stop_id/to_stop_id or from_coord/to_coord must be provided")
            start_stop = find_nearest_stop(tuple(req.from_coord), route_stops)
            end_stop = find_nearest_stop(tuple(req.to_coord), route_stops)
            stops_slice = slice_stops_by_ids(route_stops, start_stop["stop_id"], end_stop["stop_id"])

        if not stops_slice:
            raise ValueError("No stops found for given route/segment")

        # 3) derive base datetime from request (attempt parse)
        if req.timestamp_iso:
            try:
                start_dt = datetime.fromisoformat(req.timestamp_iso)
            except Exception:
                start_dt = datetime.now()
        else:
            start_dt = datetime.now()

        # 4) build feature matrix rows using your preprocessing helper
        features_rows = []
        scheduled_times = []
        for s in stops_slice:
            feat_dict = {
                "route_short_name": route_name,
                "stop_sequence": s.get("stop_sequence", 0),
                "day_of_week": start_dt.weekday(),
                "hour_of_day": start_dt.hour,
                "holiday_flag": int(req.holiday_flag or 0),
                "stop_lat": float(s.get("lat") or s.get("stop_lat") or 0.0),
                "stop_lon": float(s.get("lon") or s.get("stop_lon") or 0.0),
            }
            X_row = build_feature_vector(feat_dict)  # must produce 1D array-like
            X_arr = np.asarray(X_row).ravel()
            features_rows.append(X_arr)
            scheduled_times.append(s.get("scheduled_arrival_time"))

        if len(features_rows) == 0:
            raise ValueError("No features built for stops slice")

        # 5) Predict: try batch first, fallback to per-row
        preds: List[float] = []
        try:
            X_batch = np.vstack(features_rows)
            # silence type-checker by casting to Any for predict call
            maybe_preds = (self.model_wrapper.predict  # type: ignore
                           and self.model_wrapper.predict(X_batch))  # type: ignore
            preds = np.array(maybe_preds).astype(float).ravel().tolist()
        except Exception:
            # fallback: call your model wrapper per-row
            preds = []
            for row in features_rows:
                # your PredictionModel.predict(route_id, features_list) signature:
                p = self.model_wrapper.predict(route_name, row.tolist())  # type: ignore
                preds.append(float(p))

        # 6) compose response objects
        stops_resp = []
        total_delay = 0.0
        for s, delay, sched_time in zip(stops_slice, preds, scheduled_times):
            total_delay += float(delay)
            # compute predicted ETA using scheduled time if available
            if sched_time:
                try:
                    parts = [int(x) for x in str(sched_time).split(":")]
                    hh = parts[0] if len(parts) > 0 else start_dt.hour
                    mm = parts[1] if len(parts) > 1 else start_dt.minute
                    ss = parts[2] if len(parts) > 2 else 0
                    sched_dt = start_dt.replace(hour=hh, minute=mm, second=ss, microsecond=0)
                except Exception:
                    sched_dt = start_dt
            else:
                sched_dt = start_dt
            predicted_eta = sched_dt + timedelta(minutes=float(delay))

            stops_resp.append(
                StopPrediction(
                    stop_id=int(s.get("stop_id")),
                    stop_name=s.get("stop_name"),
                    stop_sequence=int(s.get("stop_sequence", 0)),
                    lat=float(s.get("lat") or s.get("stop_lat") or 0.0),
                    lon=float(s.get("lon") or s.get("stop_lon") or 0.0),
                    scheduled_arrival_time=s.get("scheduled_arrival_time"),
                    predicted_delay_minutes=float(delay),
                    predicted_eta_iso=predicted_eta.isoformat(),
                )
            )

        waypoints = [(float(s.get("lat") or s.get("stop_lat") or 0.0), float(s.get("lon") or s.get("stop_lon") or 0.0)) for s in stops_slice]
        summary = {"segment_stop_count": len(stops_slice), "total_predicted_delay_minutes": total_delay}

        return RouteEtaResponse(route_short_name=route_name, waypoints=waypoints, stops=stops_resp, summary=summary)


# singleton instance for routes to import
ai_routing_service = AIRoutingService()
