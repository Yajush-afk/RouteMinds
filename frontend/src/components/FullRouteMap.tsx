import { useState, useCallback } from "react";
import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix Leaflet default icon
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
  scheduled_arrival_time?: string;
  predicted_delay_minutes: number;
  predicted_eta_iso: string;
}

interface RouteEtaResponse {
  route_short_name: string;
  waypoints?: RoutePoint[];
  stops?: StopPrediction[];
  summary?: Record<string, any>;
}

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const FullRouteMap: React.FC = () => {
  const [routeName, setRouteName] = useState("");
  const [routeData, setRouteData] = useState<RouteEtaResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const defaultCenter: RoutePoint = [28.6139, 77.209]; // Delhi default

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "Invalid time";
    }
  };

  const fetchRouteData = useCallback(async () => {
    if (!routeName.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/route_eta`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ route_short_name: routeName.trim() }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Error ${res.status}`);
      }

      const data: RouteEtaResponse = await res.json();
      setRouteData(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [routeName]);

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-80 bg-white shadow-lg flex flex-col">
        <div className="p-4 bg-blue-600 text-white font-bold">Route ETA</div>

        <div className="p-4">
          <input
            type="text"
            value={routeName}
            onChange={(e) => setRouteName(e.target.value)}
            placeholder="Enter route short name"
            className="w-full p-2 border rounded"
            disabled={loading}
            onKeyPress={(e) => e.key === "Enter" && fetchRouteData()}
          />
          <button
            onClick={fetchRouteData}
            className="w-full mt-2 bg-blue-600 text-white p-2 rounded"
            disabled={loading || !routeName.trim()}
          >
            {loading ? "Loading..." : "Fetch Route"}
          </button>
        </div>

        {error && <div className="p-4 text-red-600">{error}</div>}

        <div className="flex-1 overflow-y-auto p-2">
          {routeData?.stops?.map((stop) => (
            <div key={stop.stop_id} className="p-2 border-b">
              <strong>{stop.stop_name || `Stop ${stop.stop_id}`}</strong>
              <div>Sequence: {stop.stop_sequence}</div>
              <div>Delay: {stop.predicted_delay_minutes.toFixed(1)} min</div>
              <div>ETA: {formatTime(stop.predicted_eta_iso)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1">
        <MapContainer
          center={routeData?.waypoints?.[0] || defaultCenter}
          zoom={13}
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

          {routeData?.stops?.map((stop) => (
            <Marker key={stop.stop_id} position={[stop.lat, stop.lon]}>
              <Popup>
                <div>
                  <strong>{stop.stop_name || `Stop ${stop.stop_id}`}</strong>
                  <div>Sequence: {stop.stop_sequence}</div>
                  <div>Predicted Delay: {stop.predicted_delay_minutes.toFixed(1)} min</div>
                  <div>ETA: {formatTime(stop.predicted_eta_iso)}</div>
                </div>
              </Popup>
            </Marker>
          ))}

          {routeData?.waypoints && routeData.waypoints.length > 1 && (
            <Polyline positions={routeData.waypoints} pathOptions={{ color: "blue", weight: 4 }} />
          )}
        </MapContainer>
      </div>
    </div>
  );
};

export default FullRouteMap;
