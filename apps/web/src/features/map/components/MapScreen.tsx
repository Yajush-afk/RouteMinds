import MapViewport from "@/features/map/components/MapViewport"
import MapSearchPanel from "@/features/map/components/search/MapSearchPanel"
import { useMapScreenState } from "@/features/map/hooks/useMapScreenState"

function MapScreen() {
  const { mapViewportProps, searchPanelProps } = useMapScreenState()

  return (
    <section className="relative h-screen w-full">
      <MapViewport {...mapViewportProps} />
      <MapSearchPanel {...searchPanelProps} />
    </section>
  )
}

export default MapScreen
