import { useCallback, useEffect, useState } from "react"
import { MapContainer, TileLayer, useMap } from "react-leaflet"
import type { LatLngBoundsExpression, LatLngTuple } from "leaflet"

import MapAutoLocate from "@/components/map/MapAutoLocate"
import MapClickHandler from "@/components/map/MapClickHandler"
import MapControls from "@/components/map/MapControls"
import MapMarker from "@/components/map/MapMarker"
import { isInDelhi } from "@/lib/geo"
import { searchPlaces, type SearchPlaceResult } from "@/lib/nominatim"
import {
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "@workspace/ui/components/sidebar"
import MapSidebar from "./map/MapSidebar"

const INDIA_BOUNDS: LatLngBoundsExpression = [
  [6.5, 68.0],
  [37.6, 97.5],
]
const INITIAL_MAP_CENTER: LatLngTuple = [22.9734, 78.6569]
const FALLBACK_CENTER: LatLngTuple = [28.6139, 77.209]
const DELHI_ALERT = "RouteMinds is only limited to Delhi for now."
const YOUR_LOCATION_LABEL = "Your Location"
const DESTINATION_SEARCH_DEBOUNCE_MS = 350

function MapPanTo({ position }: { position: LatLngTuple | null }) {
  const map = useMap()

  useEffect(() => {
    if (!position) {
      return
    }

    map.setView(position, Math.max(map.getZoom(), 14), { animate: true })
  }, [map, position])

  return null
}

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
  const [destinationSuggestions, setDestinationSuggestions] = useState<
    SearchPlaceResult[]
  >([])
  const [isDestinationSearching, setIsDestinationSearching] = useState(false)
  const [hasDestinationSearchAttempted, setHasDestinationSearchAttempted] =
    useState(false)
  const [panToPosition, setPanToPosition] = useState<LatLngTuple | null>(null)

  const handleFromLocationChange = useCallback((nextLocation: string) => {
    setFromLocation(nextLocation)
  }, [])

  const handleDestinationChange = useCallback((nextDestination: string) => {
    setDestination(nextDestination)

    if (!nextDestination.trim()) {
      setDestinationSuggestions([])
      setHasDestinationSearchAttempted(false)
    }
  }, [])

  const handleDestinationSelect = useCallback((result: SearchPlaceResult) => {
    const nextPosition: LatLngTuple = [result.lat, result.lon]

    if (!isInDelhi(nextPosition)) {
      alert(DELHI_ALERT)
      return
    }

    setDestination(result.displayName)
    setDestinationSuggestions([])
    setHasDestinationSearchAttempted(false)
    setMarkerPosition(nextPosition)
    setPanToPosition(nextPosition)
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

  useEffect(() => {
    const destinationQuery = destination.trim()

    if (destinationQuery.length < 3) {
      setDestinationSuggestions([])
      setIsDestinationSearching(false)
      setHasDestinationSearchAttempted(false)
      return
    }

    const controller = new AbortController()
    const timeoutId = window.setTimeout(async () => {
      setIsDestinationSearching(true)

      try {
        const results = await searchPlaces(destinationQuery, {
          signal: controller.signal,
          countryCode: "in",
          limit: 5,
        })

        const delhiResults = results.filter((result) =>
          isInDelhi([result.lat, result.lon])
        )

        setDestinationSuggestions(delhiResults)
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return
        }

        setDestinationSuggestions([])
      } finally {
        setIsDestinationSearching(false)
        setHasDestinationSearchAttempted(true)
      }
    }, DESTINATION_SEARCH_DEBOUNCE_MS)

    return () => {
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [destination])

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
          <MapPanTo position={panToPosition} />
        </MapContainer>

        <div className="pointer-events-none absolute inset-0 z-[850]">
          <div className="pointer-events-auto absolute top-0 left-4">
            <MapSidebar
              location={fromLocation}
              destination={destination}
              destinationSuggestions={destinationSuggestions}
              isDestinationSearching={isDestinationSearching}
              showNoDestinationResults={
                hasDestinationSearchAttempted &&
                destination.trim().length >= 3 &&
                destinationSuggestions.length === 0
              }
              onLocationChange={handleFromLocationChange}
              onDestinationChange={handleDestinationChange}
              onDestinationSelect={handleDestinationSelect}
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
