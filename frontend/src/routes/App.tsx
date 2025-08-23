import { ThemeProvider } from "@/components/theme-provider";
import Home from "@/pages/Home";
import Signup from "@/pages/Signup"
import Login from "@/pages/Login";
import NotFoundPage from "@/pages/NotFoundPage";
import { Route, Routes, Navigate } from "react-router-dom";
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

        <Route
          path="/login"
          element={!user ? <Login /> : <Navigate to="/" />}
        />
        <Route
          path="/sign-up"
          element={!user ? <Signup /> : <Navigate to="/" />}
        />

        {/* Example of a protected route */}
        {/* <Route path="/dashboard" element={user ? <Dashboard /> : <Navigate to="/login" />} /> */}

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ThemeProvider>
  );
}

export default App;
