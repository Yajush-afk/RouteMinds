import { Suspense, lazy } from "react"
import { Navigate, Route, Routes } from "react-router-dom"

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
        <Route path="/map" element={<MapPage />} />
        <Route path="*" element={<Navigate to="/map" replace />} />
      </Routes>
    </Suspense>
  )
}

export default App
