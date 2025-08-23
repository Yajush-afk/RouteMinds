import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { getRouteEta } from "@/utils/api";
import { signOut } from "firebase/auth";
import { auth } from "@/lib/firebase";
import AIMap from "@/components/AIMap";

export function Dashboard() {
  const { user, token, loading } = useAuth();
  const [waypoints, setWaypoints] = useState<[number, number][]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loadingETA, setLoadingETA] = useState(false);

  if (loading) return <p>Loading...</p>;
  if (!user) return <p>Please log in</p>;

  async function handleFetchETA() {
    if (!token) {
      setError("Authentication required");
      return;
    }

    setLoadingETA(true);
    setError(null);

    try {
      const eta = await getRouteEta({
        route_short_name: "720",
        timestamp_iso: new Date().toISOString(),
        holiday_flag: 0,
        token,
        // Optional: Add coordinates for a specific route
        // from_coord: [28.6139, 77.209], // Delhi coordinates as example
        // to_coord: [28.7041, 77.1025],   // Another Delhi location
      });
      
      console.log("ETA result:", eta);
      
      if (eta.waypoints && Array.isArray(eta.waypoints)) {
        setWaypoints(eta.waypoints);
      } else {
        setError("No waypoints received from server");
        setWaypoints([]);
      }
    } catch (err: any) {
      console.error("ETA fetch error:", err);
      setError(err.message || "Failed to fetch ETA");
      setWaypoints([]);
    } finally {
      setLoadingETA(false);
    }
  }

  function handleLogout() {
    signOut(auth);
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 min-h-screen gap-4">
      <div className="p-4 rounded border shadow space-y-4">
        <h1 className="text-lg font-bold">Welcome, {user.email}</h1>
        <button
          onClick={handleFetchETA}
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:bg-blue-400"
          disabled={loadingETA}
        >
          {loadingETA ? "Fetching ETA..." : "Get ETA"}
        </button>
        <button
          onClick={handleLogout}
          className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
        >
          Logout
        </button>
        {error && <p className="text-red-600">{error}</p>}
      </div>
      <div className="md:col-span-2">
        <AIMap 
          waypoints={waypoints.length > 0 ? waypoints : [[28.6139, 77.209]]} 
          zoom={12} 
        />
      </div>
    </div>
  );
}