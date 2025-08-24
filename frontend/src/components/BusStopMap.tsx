import { useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix Leaflet icons
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

export type RoutePoint = [number, number];

interface StopPrediction {
  stop_id: number;
  stop_name?: string;
  stop_sequence: number;
  lat: number;
  lon: number;
  predicted_delay_minutes: number;
  predicted_eta_iso: string;
}

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const BusStopMap: React.FC = () => {
  const [route, setRoute] = useState("");
  const [stops, setStops] = useState<StopPrediction[]>([]);

  const fetchRoute = async () => {
    if (!route.trim()) return;

    try {
      const res = await fetch(`${API_BASE}/api/predictions/route_eta`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ route_short_name: route.trim() }),
      });

      if (!res.ok) {
        console.error("Failed to fetch");
        return;
      }

      const data = await res.json();
      setStops(data.stops || []);
    } catch (err) {
      console.error(err);
    }
  };

  const defaultCenter: RoutePoint = [28.6139, 77.209]; // Delhi

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <div style={{ width: "250px", padding: "10px", background: "#f0f0f0" }}>
        <input
          type="text"
          placeholder="Enter route short name"
          value={route}
          onChange={(e) => setRoute(e.target.value)}
          style={{ width: "100%", padding: "5px" }}
        />
        <button onClick={fetchRoute} style={{ width: "100%", marginTop: "5px" }}>
          Fetch Route
        </button>

        {stops.length > 0 && (
          <ul>
            {stops.map((s) => (
              <li key={s.stop_id}>
                {s.stop_name || s.stop_id} - ETA: {new Date(s.predicted_eta_iso).toLocaleTimeString()}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div style={{ flex: 1 }}>
        <MapContainer center={defaultCenter} zoom={13} style={{ height: "100%", width: "100%" }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {stops.map((stop) => (
            <Marker key={stop.stop_id} position={[stop.lat, stop.lon]}>
              <Popup>
                <div>
                  <strong>{stop.stop_name || `Stop ${stop.stop_id}`}</strong>
                  <div>Sequence: {stop.stop_sequence}</div>
                  <div>Delay: {stop.predicted_delay_minutes} min</div>
                  <div>ETA: {new Date(stop.predicted_eta_iso).toLocaleTimeString()}</div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
};

export default BusStopMap;
