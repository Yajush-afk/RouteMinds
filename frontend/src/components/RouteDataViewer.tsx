import { useState, useCallback } from "react";

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
  waypoints?: [number, number][];
  stops?: StopPrediction[];
  summary?: Record<string, any>;
}

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const RouteDataViewer: React.FC = () => {
  const [routeName, setRouteName] = useState("");
  const [routeData, setRouteData] = useState<RouteEtaResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "Invalid time";
    }
  };

  return (
    <div className="p-4 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Route Data Viewer</h1>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={routeName}
          onChange={(e) => setRouteName(e.target.value)}
          placeholder="Enter route short name"
          className="flex-1 p-2 border rounded text-black"
          onKeyPress={(e) => e.key === "Enter" && fetchRouteData()}
        />
        <button
          onClick={fetchRouteData}
          className="px-4 py-2 bg-blue-600 text-white rounded"
          disabled={loading || !routeName.trim()}
        >
          {loading ? "Loading..." : "Fetch"}
        </button>
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      {routeData && (
        <>
          <h2 className="text-xl font-semibold mb-2">
            Route: {routeData.route_short_name}
          </h2>

          <h3 className="font-semibold mt-4 mb-2">Summary:</h3>
          <pre className="bg-gray-100 p-2 rounded">{JSON.stringify(routeData.summary, null, 2)}</pre>

          <h3 className="font-semibold mt-4 mb-2">Stops:</h3>
          {routeData.stops && routeData.stops.length > 0 ? (
            <table className="w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-200">
                  <th className="border px-2 py-1">ID</th>
                  <th className="border px-2 py-1">Name</th>
                  <th className="border px-2 py-1">Sequence</th>
                  <th className="border px-2 py-1">Lat</th>
                  <th className="border px-2 py-1">Lon</th>
                  <th className="border px-2 py-1">Scheduled</th>
                  <th className="border px-2 py-1">Predicted Delay</th>
                  <th className="border px-2 py-1">ETA</th>
                </tr>
              </thead>
              <tbody>
                {routeData.stops.map((stop) => (
                  <tr key={stop.stop_id} className="text-center">
                    <td className="border px-2 py-1">{stop.stop_id}</td>
                    <td className="border px-2 py-1">{stop.stop_name || "-"}</td>
                    <td className="border px-2 py-1">{stop.stop_sequence}</td>
                    <td className="border px-2 py-1">{stop.lat.toFixed(5)}</td>
                    <td className="border px-2 py-1">{stop.lon.toFixed(5)}</td>
                    <td className="border px-2 py-1">{stop.scheduled_arrival_time || "-"}</td>
                    <td className="border px-2 py-1">{stop.predicted_delay_minutes.toFixed(2)} min</td>
                    <td className="border px-2 py-1">{formatTime(stop.predicted_eta_iso)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No stops data available.</p>
          )}
        </>
      )}
    </div>
  );
};

export default RouteDataViewer;
