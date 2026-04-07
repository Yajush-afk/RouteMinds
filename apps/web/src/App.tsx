import { Suspense, lazy } from "react"
import { Navigate, Route, Routes } from "react-router-dom"

const LandingPage = lazy(() => import("@/pages/LandingPage"))
const MapPage = lazy(() => import("@/pages/MapPage"))

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
        <Route path="/auth" element={<Navigate to="/map" replace />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

export default App
