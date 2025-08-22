import numpy as np
import pandas as pd
import joblib
from ..config import ENCODER_PATH

try:
    route_encoder = joblib.load(ENCODER_PATH)
except Exception:
    route_encoder = None

def encode_route(route_short_name: str):
    if route_encoder is None:
        try:
            return int(route_short_name)
        except Exception:
            return 0

    return int(route_encoder.transform([str(route_short_name)])[0])

def build_feature_vector(req_dict: dict):
    """
    Input: dict with keys matching DelayRequest fields.
    Output: 1D numpy array shaped like training features order.
    Training features used:
      ['route_encoded', 'stop_sequence', 'day_of_week', 'hour_of_day', 'holiday_flag', 'stop_lat', 'stop_lon']
    """
    route_enc = encode_route(req_dict.get("route_short_name", ""))
    stop_seq = int(req_dict.get("stop_sequence", 0))
    day = int(req_dict.get("day_of_week", 0))
    hour = int(req_dict.get("hour_of_day", 0))
    holiday = int(req_dict.get("holiday_flag", 0))
    lat = float(req_dict.get("stop_lat", 0.0))
    lon = float(req_dict.get("stop_lon", 0.0))

    arr = np.array([route_enc, stop_seq, day, hour, holiday, lat, lon], dtype=float)
    return arr.reshape(1, -1)
