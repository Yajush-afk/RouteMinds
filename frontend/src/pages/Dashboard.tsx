// Dashboard.tsx
import { useAuth } from "@/hooks/useAuth";
import { getRouteEta } from "@/utils/api";
import { signOut } from "firebase/auth";
import { auth } from "@/lib/firebase"; 

export function Dashboard() {
  const { user, token, loading } = useAuth();

  if (loading) return <p>Loading...</p>;
  if (!user) return <p>Please log in</p>;

  async function handleFetchETA() {
    if (!token) return;
    try {
      const eta = await getRouteEta({
        route_short_name: "720",
        timestamp_iso: new Date().toISOString(),
        holiday_flag: 0,
        token,
      });
      console.log("ETA result:", eta);
    } catch (err) {
      console.error("ETA fetch error:", err);
    }
  }

  function handleLogout() {
    signOut(auth);
  }

  return (
    <div className="p-4">
      <h1 className="text-lg font-bold">Welcome, {user.email}</h1>
      <button
        onClick={handleFetchETA}
        className="mt-4 rounded bg-blue-600 px-4 py-2 text-white"
      >
        Get ETA
      </button>
      <button
        onClick={handleLogout}
        className="mt-4 ml-4 rounded bg-red-600 px-4 py-2 text-white"
      >
        Logout
      </button>
    </div>
  );
}
