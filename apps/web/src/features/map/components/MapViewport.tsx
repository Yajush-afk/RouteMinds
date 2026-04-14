import { memo, useCallback, useRef } from "react"
import type { MapRef } from "react-map-gl/maplibre"

import MapCameraController from "@/features/map/components/MapCameraController"
import MapCanvas from "@/features/map/components/MapCanvas"
import FeatureMapControls from "@/features/map/components/controls/MapControls"
import RouteConnectionLine from "@/features/map/components/layers/RouteConnectionLine"
import SelectedLocationMarker from "@/features/map/components/layers/SelectedLocationMarker"
import type { CameraIntent, LngLat } from "@/features/map/domain/types"

type MapViewportProps = {
  originPoint: LngLat | null
  routeOriginPoint: LngLat | null
  showOriginMarker: boolean
  userLocationPoint: LngLat | null
  destinationPoint: LngLat | null
  isLocating: boolean
  locationMessage: string | null
  cameraIntent: CameraIntent | null
  onCameraIntentHandled: () => void
  onLocateRequest: () => void
  onMapReady?: () => void
}

function MapViewport({
  originPoint,
  routeOriginPoint,
  showOriginMarker,
  userLocationPoint,
  destinationPoint,
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
        {routeOriginPoint && destinationPoint && (
          <RouteConnectionLine
            origin={routeOriginPoint}
            destination={destinationPoint}
          />
        )}
        {userLocationPoint && (
          <SelectedLocationMarker
            position={userLocationPoint}
            badge=""
            tone="origin"
            variant="user-location"
          />
        )}
        {originPoint && showOriginMarker && (
          <SelectedLocationMarker
            position={originPoint}
            badge="A"
            tone="origin"
          />
        )}
        {destinationPoint && (
          <SelectedLocationMarker
            position={destinationPoint}
            badge="B"
            tone="destination"
          />
        )}
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
