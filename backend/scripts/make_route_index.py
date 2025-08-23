import pandas as pd
import json
from pathlib import Path

CSV_PATH = Path("data/processed/bus_delay_dataset.csv")  
OUT_PATH = Path("data/processed/route_index.json")       

def build_route_index():
    df = pd.read_csv(CSV_PATH)

    df = df[["route_id", "stop_id", "stop_sequence"]].dropna()

    df["stop_sequence"] = pd.to_numeric(df["stop_sequence"], errors="coerce")
    df = df.dropna(subset=["stop_sequence"])
    df["stop_sequence"] = df["stop_sequence"].astype(int)

    route_index = {}
    for route_id, group in df.groupby("route_id"):
        ordered_stops = (
            group.sort_values("stop_sequence")["stop_id"].astype(str).tolist()
        )
        route_index[str(route_id)] = ordered_stops

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(route_index, f, indent=2)

    print(f"Route index saved to {OUT_PATH}")

if __name__ == "__main__":
    build_route_index()
