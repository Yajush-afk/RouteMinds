import { Suspense, lazy } from "react"
import { Navigate, Route, Routes } from "react-router-dom"

import ProtectedRoute from "@/auth/ProtectedRoute"

const LandingPage = lazy(() => import("@/pages/LandingPage"))
const MapPage = lazy(() => import("@/pages/MapPage"))
const AuthPage = lazy(() => import("@/pages/AuthPage"))
const LegacyAuthRedirect = lazy(
  () => import("@/components/auth/LegacyAuthRedirect")
)

function RouteFallback() {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-6 text-center text-sm text-muted-foreground">
      Loading route...
    </main>
  )
}

export function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/login" element={<LegacyAuthRedirect />} />
        <Route path="/signup" element={<LegacyAuthRedirect />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/map" element={<MapPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

export default App
