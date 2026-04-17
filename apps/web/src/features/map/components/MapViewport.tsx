import { memo, useCallback, useRef } from "react"
import type { MapRef } from "react-map-gl/maplibre"

import MapCameraController from "@/features/map/components/MapCameraController"
import MapCanvas from "@/features/map/components/MapCanvas"
import FeatureMapControls from "@/features/map/components/controls/MapControls"
import PlannedRouteLines from "@/features/map/components/layers/PlannedRouteLines"
import SelectedLocationMarker from "@/features/map/components/layers/SelectedLocationMarker"
import type {
  CameraIntent,
  LngLat,
  RouteLegPlan,
  WaypointMarker,
} from "@/features/map/domain/types"

type MapViewportProps = {
  waypointMarkers: WaypointMarker[]
  routeLegs: RouteLegPlan[]
  userLocationPoint: LngLat | null
  isLocating: boolean
  locationMessage: string | null
  cameraIntent: CameraIntent | null
  onCameraIntentHandled: () => void
  onLocateRequest: () => void
  onMapReady?: () => void
}

function MapViewport({
  waypointMarkers,
  routeLegs,
  userLocationPoint,
  isLocating,
  locationMessage,
  cameraIntent,
  onCameraIntentHandled,
  onLocateRequest,
  onMapReady,
}: MapViewportProps) {
  const mapRef = useRef<MapRef | null>(null)

  const handleZoomIn = useCallback(() => {
    mapRef.current?.zoomIn()
  }, [])

  const handleZoomOut = useCallback(() => {
    mapRef.current?.zoomOut()
  }, [])

  return (
    <>
      <MapCanvas
        ref={mapRef}
        className="absolute inset-0 h-full w-full"
        onReady={onMapReady}
      >
        <MapCameraController
          mapRef={mapRef}
          intent={cameraIntent}
          onHandled={onCameraIntentHandled}
        />
        <PlannedRouteLines routeLegs={routeLegs} />
        {userLocationPoint && (
          <SelectedLocationMarker
            position={userLocationPoint}
            badge=""
            tone="origin"
            variant="user-location"
          />
        )}
        {waypointMarkers.map((marker) => (
          <SelectedLocationMarker
            key={marker.id}
            position={marker.position}
            badge={marker.badge}
            tone={marker.tone}
          />
        ))}
      </MapCanvas>

      {isLocating && (
        <div className="pointer-events-none absolute inset-0 z-900 grid place-items-center bg-background/60 backdrop-blur-[1px]">
          <p className="rounded-md bg-card px-3 py-2 text-sm text-card-foreground shadow-sm">
            Getting your location...
          </p>
        </div>
      )}

      {locationMessage && (
        <p className="absolute bottom-4 left-4 z-1000 rounded-md bg-card px-3 py-2 text-xs text-card-foreground shadow-sm">
          {locationMessage}
        </p>
      )}

      <FeatureMapControls
        onLocateRequest={onLocateRequest}
        isLocating={isLocating}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
      />
    </>
  )
}

export default memo(MapViewport)
