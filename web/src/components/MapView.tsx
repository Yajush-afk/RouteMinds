import { useCallback, useState } from "react"
import { MapContainer, TileLayer } from "react-leaflet"
import type { LatLngBoundsExpression, LatLngTuple } from "leaflet"

import MapAutoLocate from "@/components/map/MapAutoLocate"
import MapClickHandler from "@/components/map/MapClickHandler"
import MapControls from "@/components/map/MapControls"
import MapMarker from "@/components/map/MapMarker"
import { isInDelhi } from "@/lib/geo"

const INDIA_BOUNDS: LatLngBoundsExpression = [
  [6.5, 68.0],
  [37.6, 97.5],
]
const INITIAL_MAP_CENTER: LatLngTuple = [22.9734, 78.6569]
const FALLBACK_CENTER: LatLngTuple = [28.6139, 77.209]
const DELHI_ALERT = "RouteMinds is only limited to Delhi for now."

function MapView() {
  // Single source of truth for the active marker allowed within Delhi.
  const [markerPosition, setMarkerPosition] = useState<LatLngTuple | null>(null)
  const [isLocating, setIsLocating] = useState(true)
  const [locationError, setLocationError] = useState<string | null>(null)

  const placeMarkerIfAllowed = useCallback((nextPosition: LatLngTuple) => {
    if (isInDelhi(nextPosition)) {
      setMarkerPosition(nextPosition)
    }
  }, [])

  const handleLocateStart = useCallback(() => {
    setIsLocating(true)
    setLocationError(null)
  }, [])

  const handleLocateSuccess = useCallback((nextPosition: LatLngTuple) => {
    if (isInDelhi(nextPosition)) {
      setMarkerPosition(nextPosition)
    } else {
      alert(DELHI_ALERT)
    }

    setIsLocating(false)
    setLocationError(null)
  }, [])

  const handleLocateError = useCallback((message: string) => {
    // If location access fails, we still render a usable map with a known fallback.
    setMarkerPosition((currentPosition) => currentPosition ?? FALLBACK_CENTER)
    setIsLocating(false)
    setLocationError(message)
  }, [])

  return (
    <section className="relative h-screen w-full">
      <MapContainer
        center={markerPosition ?? INITIAL_MAP_CENTER}
        zoom={13}
        maxBounds={INDIA_BOUNDS}
        maxBoundsViscosity={1}
        minZoom={5}
        className="h-full w-full"
        zoomControl={false}
        scrollWheelZoom={true}
        touchZoom={true}
        dragging={true}
        doubleClickZoom={true}
        attributionControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapAutoLocate
          onLocateStart={handleLocateStart}
          onLocateSuccess={handleLocateSuccess}
          onLocateError={handleLocateError}
        />
        {markerPosition && (
          <>
            <MapMarker
              position={markerPosition}
              isAllowedPosition={isInDelhi}
              onPositionChange={setMarkerPosition}
            />
          </>
        )}
        <MapClickHandler
          onSingleClickPan={() => {
            // `MapClickHandler` already pans map to clicked point; no marker action.
          }}
          onContextMenuPlace={placeMarkerIfAllowed}
        />
        <MapControls
          isLocating={isLocating}
          onLocateStart={handleLocateStart}
          onLocateSuccess={handleLocateSuccess}
          onLocateError={handleLocateError}
        />
      </MapContainer>

      {isLocating && (
        <div className="pointer-events-none absolute inset-0 z-[900] grid place-items-center bg-background/60 backdrop-blur-[1px]">
          <p className="rounded-md bg-card px-3 py-2 text-sm text-card-foreground shadow-sm">
            Getting your location...
          </p>
        </div>
      )}

      {locationError && (
        <p className="absolute bottom-4 left-4 z-[1000] rounded-md bg-card px-3 py-2 text-xs text-card-foreground shadow-sm">
          {locationError}
        </p>
      )}
    </section>
  )
}

export default MapView
