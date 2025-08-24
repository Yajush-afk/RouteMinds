# backend/services/ai_routing.py
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, List
import numpy as np
from ..models.prediction import PredictionModel
from ..utils.route_index import get_stops_for_route, find_nearest_stop, slice_stops_by_ids
from ..utils.preprocessing import build_feature_vector

BASE = Path(__file__).resolve().parents[1]  # backend/
MODEL_P = BASE / "models" / "trained_model.pkl"
ENCODER_P = BASE / "models" / "route_label_encoder.pkl"

_model_wrapper = PredictionModel(str(MODEL_P), str(ENCODER_P))

class AIRoutingService:
    def __init__(self, model_wrapper: Optional[Any] = None, index_path: Optional[str] = None):
        self.model_wrapper: Any = model_wrapper or _model_wrapper
        self.index_path = index_path

    def compute_route_eta(self, req: Any) -> Any:
        from ..schemas.route_eta import RouteEtaRequest, RouteEtaResponse, StopPrediction

        if not isinstance(req, RouteEtaRequest):
            req = RouteEtaRequest.model_validate(req)

        route_name = req.route_short_name
        route_stops = get_stops_for_route(route_name, self.index_path)

        if req.from_stop_id and req.to_stop_id:
            stops_slice = slice_stops_by_ids(route_stops, req.from_stop_id, req.to_stop_id)
        else:
            if not req.from_coord or not req.to_coord:
                raise ValueError("from_stop_id/to_stop_id or from_coord/to_coord required")
            start_stop = find_nearest_stop(tuple(req.from_coord), route_stops)
            end_stop = find_nearest_stop(tuple(req.to_coord), route_stops)
            stops_slice = slice_stops_by_ids(route_stops, start_stop["stop_id"], end_stop["stop_id"])

        if not stops_slice:
            raise ValueError("No stops found for given route/segment")

        start_dt = datetime.fromisoformat(req.timestamp_iso) if req.timestamp_iso else datetime.now()

        features_rows, scheduled_times = [], []
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
            X_row = build_feature_vector(feat_dict)
            features_rows.append(np.asarray(X_row).ravel())
            scheduled_times.append(s.get("scheduled_arrival_time"))

        if not features_rows:
            raise ValueError("No features built for stops slice")

        preds = [float(self.model_wrapper.predict(route_name, row.tolist())) for row in features_rows]

        stops_resp, total_delay = [], 0.0
        for s, delay, sched_time in zip(stops_slice, preds, scheduled_times):
            total_delay += float(delay)
            if sched_time:
                try:
                    parts = [int(x) for x in str(sched_time).split(":")]
                    hh, mm, ss = parts[0], parts[1], parts[2] if len(parts) > 2 else 0
                    sched_dt = start_dt.replace(hour=hh, minute=mm, second=ss, microsecond=0)
                except Exception:
                    sched_dt = start_dt
            else:
                sched_dt = start_dt

            predicted_eta = sched_dt + timedelta(minutes=float(delay))
            stops_resp.append(StopPrediction(
                stop_id=int(s.get("stop_id")),
                stop_name=s.get("stop_name"),
                stop_sequence=int(s.get("stop_sequence", 0)),
                lat=float(s.get("lat") or s.get("stop_lat") or 0.0),
                lon=float(s.get("lon") or s.get("stop_lon") or 0.0),
                scheduled_arrival_time=s.get("scheduled_arrival_time"),
                predicted_delay_minutes=float(delay),
                predicted_eta_iso=predicted_eta.isoformat(),
            ))

        waypoints = [(float(s.get("lat") or s.get("stop_lat") or 0.0),
                      float(s.get("lon") or s.get("stop_lon") or 0.0)) for s in stops_slice]

        summary = {"segment_stop_count": len(stops_slice), "total_predicted_delay_minutes": total_delay}

        return RouteEtaResponse(route_short_name=route_name, waypoints=waypoints, stops=stops_resp, summary=summary)


ai_routing_service = AIRoutingService(index_path="data/processed/route_index.json")
