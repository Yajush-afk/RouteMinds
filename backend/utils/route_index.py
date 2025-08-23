# backend/utils/route_index.py
import json
from pathlib import Path
import math
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
DEFAULT_INDEX_PATH = BASE_DIR / "data" / "route_stops_index.json"

def haversine_km(a, b):
    # a, b = (lat, lon)
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * R * math.asin(math.sqrt(x))

@lru_cache(maxsize=1)
def load_route_index(path=None):
    p = Path(path) if path else DEFAULT_INDEX_PATH
    if not p.exists():
        # return empty dict rather than error so editor/type checkers don't complain.
        raise FileNotFoundError(f"Route index file not found at {p}")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def get_stops_for_route(route_short_name, index_path=None):
    idx = load_route_index(index_path)
    if route_short_name not in idx:
        raise KeyError(f"Route {route_short_name} not found in route index")
    return idx[route_short_name]

def find_nearest_stop(coord, route_stops):
    if not route_stops:
        raise ValueError("route_stops empty")
    best = None
    best_d = float("inf")
    for s in route_stops:
        # expecting s has keys "lat","lon"
        lat = float(s.get("lat") or s.get("stop_lat") or 0.0)
        lon = float(s.get("lon") or s.get("stop_lon") or 0.0)
        d = haversine_km(coord, (lat, lon))
        if d < best_d:
            best_d = d
            best = s
    return best

def slice_stops_by_ids(route_stops, from_id, to_id):
    ids = [int(s["stop_id"]) for s in route_stops]
    try:
        i = ids.index(int(from_id))
        j = ids.index(int(to_id))
    except ValueError:
        raise KeyError("from_stop_id or to_stop_id not present on route")
    if i <= j:
        return route_stops[i:j+1]
    else:
        # reverse travel case: return in forward order (j..i) reversed to keep chronological sequence
        return list(reversed(route_stops[j:i+1]))
