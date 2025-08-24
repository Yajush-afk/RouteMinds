import { useState, useCallback } from "react";
import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { Search, MapPin, Clock, AlertCircle, RefreshCw, X, Navigation } from "lucide-react";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// Fix default icon issue
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
  waypoints: RoutePoint[];
  stops: StopPrediction[];
  summary: Record<string, any>;
}

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const RoutePredictionMap: React.FC = () => {
  const [routeShortName, setRouteShortName] = useState<string>("");
  const [waypoints, setWaypoints] = useState<RoutePoint[]>([]);
  const [stops, setStops] = useState<StopPrediction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [inputFocused, setInputFocused] = useState(false);
  const [recentRoutes] = useState<string[]>(["101", "102", "103", "201"]); // Mock recent routes

  const fetchRouteData = useCallback(async (route: string) => {
    if (!route.trim()) {
      setError("Please enter a route name");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = ""; // Replace with your Firebase auth token if needed
      const res = await fetch(`${API_BASE}/api/predictions/route_eta`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ route_short_name: route.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `Request failed with status ${res.status}`);
      }

      const data: RouteEtaResponse = await res.json();
      if (!data.waypoints || data.waypoints.length === 0) {
        throw new Error("No route data available");
      }

      setWaypoints(data.waypoints);
      setStops(data.stops || []);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err.message || "Unknown error occurred");
      console.error("Route fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRouteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.toUpperCase(); // Auto-uppercase for route names
    setRouteShortName(value);
    if (error && value.trim()) setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !loading && routeShortName.trim()) {
      fetchRouteData(routeShortName);
      setInputFocused(false);
    }
    if (e.key === "Escape") {
      setInputFocused(false);
    }
  };

  const clearInput = () => {
    setRouteShortName("");
    setError(null);
    setWaypoints([]);
    setStops([]);
    setLastUpdated(null);
  };

  const selectRecentRoute = (route: string) => {
    setRouteShortName(route);
    setInputFocused(false);
    fetchRouteData(route);
  };

  const formatTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "Invalid time";
    }
  };

  const getDelayColor = (delayMinutes: number) => {
    if (delayMinutes <= 0) return "text-green-600";
    if (delayMinutes <= 5) return "text-yellow-600";
    return "text-red-600";
  };

  const defaultCenter: RoutePoint = [28.6139, 77.209]; // Delhi
  const mapCenter: RoutePoint = waypoints.length > 0 ? waypoints[0] : defaultCenter;

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div className="w-80 bg-white shadow-lg flex flex-col">
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 font-bold flex items-center gap-2">
          <Navigation className="w-5 h-5" />
          Route Predictions
        </div>

        <div className="p-4 border-b border-gray-200 relative z-20">
          {/* Enhanced Input Field */}
          <div className="relative z-10">
            <div className={`relative transition-all duration-200 ${
              inputFocused ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
            }`}>
              <input
                type="text"
                placeholder="Enter route (e.g., 101, A1, BRT-1)"
                value={routeShortName}
                onChange={handleRouteChange}
                onKeyDown={handleKeyDown}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setTimeout(() => setInputFocused(false), 150)}
                className={`w-full pl-10 pr-10 py-3 border rounded-lg focus:outline-none transition-all duration-200 ${
                  error 
                    ? 'border-red-300 bg-red-50 focus:border-red-500' 
                    : 'border-gray-300 focus:border-blue-500 focus:bg-blue-50'
                } ${loading ? 'bg-gray-50' : ''}`}
                disabled={loading}
                maxLength={10}
                autoComplete="off"
                spellCheck="false"
              />
              <Search className={`absolute left-3 top-3.5 w-4 h-4 transition-colors duration-200 ${
                inputFocused ? 'text-blue-500' : 'text-gray-400'
              }`} />
              {routeShortName && !loading && (
                <button
                  onClick={clearInput}
                  className="absolute right-3 top-3.5 w-4 h-4 text-gray-400 hover:text-red-500 transition-colors duration-200"
                  type="button"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Recent Routes Dropdown */}
            {inputFocused && recentRoutes.length > 0 && !routeShortName && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-xl z-[100] max-h-40 overflow-y-auto">
                <div className="px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b rounded-t-lg">
                  Recent Routes
                </div>
                {recentRoutes.map((route) => (
                  <button
                    key={route}
                    onClick={() => selectRecentRoute(route)}
                    className="w-full px-3 py-2 text-left hover:bg-blue-50 hover:text-blue-700 transition-colors duration-150 flex items-center gap-2 text-sm"
                  >
                    <MapPin className="w-3 h-3 text-gray-400" />
                    <span className="font-mono">{route}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Enhanced Search Button */}
          <button
            onClick={() => fetchRouteData(routeShortName)}
            disabled={loading || !routeShortName.trim()}
            className={`w-full mt-3 py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-all duration-200 ${
              loading || !routeShortName.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white shadow-md hover:shadow-lg transform hover:-translate-y-0.5'
            }`}
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                Get Live Predictions
              </>
            )}
          </button>

          {/* Input Helper Text */}
          <div className="mt-2 text-xs text-gray-500">
            Try: 101, A1, BRT-1, or press Enter to search
          </div>
        </div>

        {/* Enhanced Error Display */}
        {error && (
          <div className="mx-4 mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Enhanced Success Indicator */}
        {lastUpdated && !error && (
          <div className="mx-4 mt-2 p-2 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 text-xs text-green-700">
              <Clock className="w-3 h-3 text-green-600 flex-shrink-0" />
              <span>Updated: {lastUpdated.toLocaleTimeString()}</span>
              <span className="ml-auto px-2 py-0.5 bg-green-100 text-green-800 rounded-full text-xs">
                Live
              </span>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4">
          {stops.map((stop) => (
            <div key={stop.stop_id} className="mb-2 p-3 border rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors duration-150">
              <div className="flex justify-between items-start">
                <span className="font-medium text-gray-900">{stop.stop_name || `Stop ${stop.stop_id}`}</span>
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                  #{stop.stop_sequence}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm mt-2">
                <span className="text-gray-600">ETA: {formatTime(stop.predicted_eta_iso)}</span>
                <span className={`font-medium ${getDelayColor(stop.predicted_delay_minutes)}`}>
                  {stop.predicted_delay_minutes > 0 ? '+' : ''}{stop.predicted_delay_minutes.toFixed(1)} min
                </span>
              </div>
            </div>
          ))}
          {stops.length === 0 && !loading && !error && (
            <div className="text-center text-gray-400 mt-8">
              <MapPin className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>Enter a route number to see live predictions</p>
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        <MapContainer center={mapCenter} zoom={12} className="h-full w-full">
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {waypoints.length > 1 && <Polyline positions={waypoints} pathOptions={{ color: "blue", weight: 4 }} />}
          {stops.map((stop) => (
            <Marker key={stop.stop_id} position={[stop.lat, stop.lon]}>
              <Popup>
                <div>
                  <strong>{stop.stop_name}</strong>
                  <div>ETA: {formatTime(stop.predicted_eta_iso)}</div>
                  <div>Delay: {stop.predicted_delay_minutes.toFixed(1)} min</div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
};

export default RoutePredictionMap;