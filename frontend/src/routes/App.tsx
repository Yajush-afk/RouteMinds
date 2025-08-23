import { ThemeProvider } from "@/components/theme-provider";
import Home from "@/pages/Home";
import Signup from "@/pages/Signup";
import Login from "@/pages/Login";
import NotFoundPage from "@/pages/NotFoundPage";
import { Route, Routes, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import BackendCheck from "@/components/BackendCheck";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import AIMap from "@/components/AIMap";
import { Dashboard } from "@/pages/Dashboard";

const optimizedRoute: [number, number][] = [
  [28.6139, 77.209], // Start point (Delhi)
  [28.62, 77.21], // Waypoint
  [28.635, 77.22], // Waypoint
  [28.65, 77.23], // End point
];

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        Loading...
      </div>
    );
  }

  return (
    <ThemeProvider defaultTheme="system" storageKey="theme">
      <Routes>
        <Route path="/" element={<Home />} />

        <Route
          path="/login"
          element={!user ? <Login /> : <Navigate to="/" />}
        />
        <Route
          path="/sign-up"
          element={!user ? <Signup /> : <Navigate to="/" />}
        />
        <Route path="/check-backend" element={<BackendCheck />} />

        {/* Example of a protected route */}
        {/* <Route path="/dashboard" element={user ? <Dashboard /> : <Navigate to="/login" />} /> */}

        <Route path="*" element={<NotFoundPage />} />
        <Route
          path="/map"
          element={
            <ProtectedRoute>
              <AIMap waypoints={optimizedRoute} zoom={16} />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
