import { forwardRef, useMemo } from "react"
import Map from "react-map-gl/maplibre"
import type { MapLayerMouseEvent } from "maplibre-gl"
import type { PropsWithChildren } from "react"
import type { MapRef } from "react-map-gl/maplibre"

import {
  OPENFREEMAP_ATTRIBUTION,
  OPENFREEMAP_STYLE_URL,
} from "@/features/map/config/mapStyle"
import {
  DEFAULT_MAP_ZOOM,
  INDIA_BOUNDS,
  INITIAL_MAP_CENTER,
  MIN_MAP_ZOOM,
} from "@/features/map/domain/mapDefaults"
import type { LngLat } from "@/features/map/domain/types"
import { cn } from "@workspace/ui/lib/utils"

type MapCanvasProps = PropsWithChildren<{
  center?: LngLat | null
  zoom?: number
  onMapClick?: (position: LngLat) => void
  className?: string
}>

const MapCanvas = forwardRef<MapRef, MapCanvasProps>(function MapCanvas(
  { center, zoom = DEFAULT_MAP_ZOOM, onMapClick, className, children },
  ref
) {
  const initialViewState = useMemo(
    () => ({
      longitude: center?.lng ?? INITIAL_MAP_CENTER.lng,
      latitude: center?.lat ?? INITIAL_MAP_CENTER.lat,
      zoom,
    }),
    [center, zoom]
  )

  const maxBounds = useMemo(
    () =>
      [
        [INDIA_BOUNDS.southWest.lng, INDIA_BOUNDS.southWest.lat],
        [INDIA_BOUNDS.northEast.lng, INDIA_BOUNDS.northEast.lat],
      ] as [[number, number], [number, number]],
    []
  )

  function handleMapClick(event: MapLayerMouseEvent) {
    if (!onMapClick) {
      return
    }

    onMapClick({
      lng: event.lngLat.lng,
      lat: event.lngLat.lat,
    })
  }

  return (
    <div className={cn("absolute inset-0 h-full w-full", className)}>
      <Map
        ref={ref}
        initialViewState={initialViewState}
        mapStyle={OPENFREEMAP_STYLE_URL}
        maxBounds={maxBounds}
        minZoom={MIN_MAP_ZOOM}
        attributionControl={false}
        dragRotate={false}
        doubleClickZoom={true}
        touchZoomRotate={true}
        onClick={handleMapClick}
      >
        {children}
        <div className="pointer-events-none absolute right-3 bottom-3 z-10 rounded-md bg-background/85 px-2 py-1 text-[11px] text-muted-foreground shadow-sm backdrop-blur supports-backdrop-filter:bg-background/70">
          <span dangerouslySetInnerHTML={{ __html: OPENFREEMAP_ATTRIBUTION }} />
        </div>
      </Map>
    </div>
  )
})

export default MapCanvas
