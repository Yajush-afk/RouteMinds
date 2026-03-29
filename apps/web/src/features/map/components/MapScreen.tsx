import { useRef } from "react"

import MapCameraController from "@/features/map/components/MapCameraController"
import MapCanvas from "@/features/map/components/MapCanvas"
import MapSearchBar from "@/features/map/components/search/MapSearchBar"
import { useMapScreenState } from "@/features/map/hooks/useMapScreenState"
import type { MapRef } from "react-map-gl/maplibre"
import SelectedLocationMarker from "@/features/map/components/layers/SelectedLocationMarker"
import FeatureMapControls from "@/features/map/components/controls/MapControls"

function MapScreen() {
  const mapRef = useRef<MapRef | null>(null)

  const {
    selectedPoint,
    originLabel,
    originResults,
    isOriginSearching,
    showNoOriginResults,
    destinationText,
    destinationResults,
    isDestinationSearching,
    showNoDestinationResults,
    isLocating,
    locationMessage,
    cameraIntent,
    handleLocationChange,
    handleOriginFocus,
    handleOriginBlur,
    handleOriginSelect,
    handleDestinationChange,
    handleDestinationSelect,
    handleMapSelect,
    handleMarkerDragEnd,
    handleCameraIntentHandled,
    handleLocateRequest,
  } = useMapScreenState()

  function handleZoomIn() {
    mapRef.current?.zoomIn()
  }

  function handleZoomOut() {
    mapRef.current?.zoomOut()
  }

  return (
    <section className="relative h-screen w-full">
      <MapCanvas
        center={selectedPoint}
        ref={mapRef}
        onMapClick={handleMapSelect}
        className="absolute inset-0 h-full w-full"
      >
        <MapCameraController
          mapRef={mapRef}
          intent={cameraIntent}
          onHandled={handleCameraIntentHandled}
        />
        {selectedPoint && (
          <SelectedLocationMarker
            position={selectedPoint}
            onDragEnd={handleMarkerDragEnd}
          />
        )}
      </MapCanvas>

      <div className="pointer-events-none absolute inset-0 z-850">
        <MapSearchBar
          originText={originLabel}
          originResults={originResults}
          isOriginSearching={isOriginSearching}
          showNoOriginResults={showNoOriginResults}
          destinationText={destinationText}
          destinationResults={destinationResults}
          isDestinationSearching={isDestinationSearching}
          showNoDestinationResults={showNoDestinationResults}
          onOriginChange={handleLocationChange}
          onOriginFocus={handleOriginFocus}
          onOriginBlur={handleOriginBlur}
          onOriginSelect={handleOriginSelect}
          onDestinationChange={handleDestinationChange}
          onDestinationSelect={handleDestinationSelect}
        />
      </div>

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
        onLocateRequest={handleLocateRequest}
        isLocating={isLocating}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
      />
    </section>
  )
}

export default MapScreen
