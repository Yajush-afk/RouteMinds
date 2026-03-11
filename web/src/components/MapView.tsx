import { useCallback, useState } from "react"
import { MapContainer, TileLayer } from "react-leaflet"
import type { LatLngBoundsExpression, LatLngTuple } from "leaflet"

import MapAutoLocate from "@/components/map/MapAutoLocate"
import MapClickHandler from "@/components/map/MapClickHandler"
import MapControls from "@/components/map/MapControls"
import MapMarker from "@/components/map/MapMarker"
import { isInDelhi } from "@/lib/geo"
import {
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar"
import MapSidebar from "./map/MapSidebar"

const INDIA_BOUNDS: LatLngBoundsExpression = [
  [6.5, 68.0],
  [37.6, 97.5],
]
const INITIAL_MAP_CENTER: LatLngTuple = [22.9734, 78.6569]
const FALLBACK_CENTER: LatLngTuple = [28.6139, 77.209]
const DELHI_ALERT = "RouteMinds is only limited to Delhi for now."
const YOUR_LOCATION_LABEL = "Your Location"

function FloatingSidebarTrigger() {
  const { isMobile, state } = useSidebar()
  const triggerPositionClass = isMobile
    ? "left-4"
    : state === "collapsed"
      ? "left-4"
      : "left-[calc(var(--sidebar-width)+1rem)]"

  return (
    <SidebarTrigger
      className={`absolute top-4 z-[1000] bg-card/90 shadow-md backdrop-blur transition-[left,opacity,filter] duration-200 ease-out supports-[backdrop-filter]:bg-card/75 ${triggerPositionClass}`}
    />
  )
}

function MapView() {
  // Single source of truth for the active marker allowed within Delhi.
  const [markerPosition, setMarkerPosition] = useState<LatLngTuple | null>(null)
  const [isLocating, setIsLocating] = useState(true)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [fromLocation, setFromLocation] = useState("")
  const [destination, setDestination] = useState("")

  const handleFromLocationChange = useCallback((nextLocation: string) => {
    setFromLocation(nextLocation)
  }, [])

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
      setFromLocation(YOUR_LOCATION_LABEL)
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
    <SidebarProvider>
      <section className="relative h-screen w-full">
        <MapContainer
          center={markerPosition ?? INITIAL_MAP_CENTER}
          zoom={13}
          maxBounds={INDIA_BOUNDS}
          maxBoundsViscosity={1}
          minZoom={5}
          className="absolute inset-0 z-0 h-full w-full"
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

        <div className="pointer-events-none absolute inset-0 z-[850]">
          <div className="pointer-events-auto absolute top-0 left-4">
            <MapSidebar
              location={fromLocation}
              destination={destination}
              onLocationChange={handleFromLocationChange}
              onDestinationChange={setDestination}
            />
          </div>
        </div>

        <FloatingSidebarTrigger />

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
    </SidebarProvider>
  )
}

export default MapView
