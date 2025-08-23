import { ThemeProvider } from "@/components/theme-provider";
import Home from "@/pages/Home";
import Signup from "@/pages/Signup";
import Login from "@/pages/Login";
import NotFoundPage from "@/pages/NotFoundPage";
import { Route, Routes, Navigate } from "react-router-dom";
import BackendCheck from "@/components/BackendCheck";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import AIMap from "@/components/AIMap";
import { Dashboard } from "@/pages/Dashboard";
import { useAuth } from "@/hooks/useAuth";

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
        <Route path="/login" element={!user ? <Login /> : <Navigate to="/dashboard" />} />
        <Route path="/sign-up" element={!user ? <Signup /> : <Navigate to="/dashboard" />} />
        <Route path="/check-backend" element={<BackendCheck />} />

        {/* Map page with default center */}
        <Route
          path="/map"
          element={
            <ProtectedRoute>
              <AIMap waypoints={[[28.6139, 77.209]]} zoom={16} />
            </ProtectedRoute>
          }
        />

        {/* Dashboard dynamically fetches waypoints */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
