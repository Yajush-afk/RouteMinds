import { useEffect, useState } from "react";
import { getAuth } from "firebase/auth";

const API_BASE = "http://localhost:8000"; // adjust if backend runs elsewhere

type Status = "idle" | "loading" | "success" | "error" | "unauth";

const BackendCheck: React.FC = () => {
  const [pingStatus, setPingStatus] = useState<Status>("idle");
  const [pingData, setPingData] = useState<any>(null);

  const [protectedStatus, setProtectedStatus] = useState<Status>("idle");
  const [protectedData, setProtectedData] = useState<any>(null);

  // Test public endpoint (/ping)
  useEffect(() => {
    const checkPing = async () => {
      setPingStatus("loading");
      try {
        const res = await fetch(`${API_BASE}/ping`);
        const data = await res.json();
        setPingData(data);
        setPingStatus("success");
      } catch {
        setPingStatus("error");
      }
    };
    checkPing();
  }, []);

  // Test protected endpoint (/protected)
  const checkProtected = async () => {
    setProtectedStatus("loading");
    try {
      const auth = getAuth();
      const user = auth.currentUser;

      if (!user) {
        setProtectedStatus("unauth");
        return;
      }

      const token = await user.getIdToken();
      const res = await fetch(`${API_BASE}/protected`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = await res.json();

      if (res.ok) {
        setProtectedData(data);
        setProtectedStatus("success");
      } else {
        setProtectedStatus("error");
      }
    } catch {
      setProtectedStatus("error");
    }
  };

  const statusBadge = (status: Status) => {
    switch (status) {
      case "loading":
        return <span className="text-gray-500 italic">Checking…</span>;
      case "success":
        return <span className="text-gray-800 font-medium">✓ Success</span>;
      case "error":
        return <span className="text-gray-800 font-medium">✕ Error</span>;
      case "unauth":
        return <span className="text-gray-600">User not logged in</span>;
      default:
        return <span className="text-gray-400">–</span>;
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="p-6 rounded-xl border border-gray-300 shadow-sm max-w-lg w-full space-y-4 bg-primary">
        <h2 className="text-xl font-semibold mb-4 text-center text-gray-800">
          Backend Connectivity Test
        </h2>

        {/* Ping card */}
        <div className="p-4 rounded-lg border border-gray-200 bg-gray-50">
          <div className="flex justify-between items-center mb-2">
            <p className="font-medium text-gray-700">/ping</p>
            {statusBadge(pingStatus)}
          </div>
          {pingData && (
            <pre className="bg-gray-100 p-2 rounded text-xs text-gray-700">
              {JSON.stringify(pingData, null, 2)}
            </pre>
          )}
        </div>

        {/* Protected card */}
        <div className="p-4 rounded-lg border border-gray-200 bg-gray-50">
          <div className="flex justify-between items-center mb-2">
            <p className="font-medium text-gray-700">/protected</p>
            {statusBadge(protectedStatus)}
          </div>
          <button
            onClick={checkProtected}
            className="px-3 py-2 bg-gray-800 text-white rounded hover:bg-gray-700 disabled:opacity-50"
            disabled={protectedStatus === "loading"}
          >
            Test /protected
          </button>
          {protectedData && (
            <pre className="bg-gray-100 p-2 rounded text-xs text-gray-700 mt-2">
              {JSON.stringify(protectedData, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default BackendCheck;
