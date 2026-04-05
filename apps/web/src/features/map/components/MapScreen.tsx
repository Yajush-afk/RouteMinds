import AuthenticatedApiStatus from "@/features/auth/components/AuthenticatedApiStatus"
import MapViewport from "@/features/map/components/MapViewport"
import MapSearchPanel from "@/features/map/components/search/MapSearchPanel"
import { useBackendHealth } from "@/features/map/hooks/useBackendHealth"
import { useMapScreenState } from "@/features/map/hooks/useMapScreenState"

function MapScreen() {
  const backendHealth = useBackendHealth()
  const { mapViewportProps, searchPanelProps } = useMapScreenState()

  return (
    <section className="relative h-screen w-full">
      <MapViewport {...mapViewportProps} />
      <MapSearchPanel {...searchPanelProps} backendHealth={backendHealth} />
      <AuthenticatedApiStatus />
    </section>
  )
}

export default MapScreen
