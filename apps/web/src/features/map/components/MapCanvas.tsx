import { forwardRef, memo } from "react"
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
  DELHI_BOUNDS,
  INITIAL_MAP_CENTER,
  MIN_MAP_ZOOM,
} from "@/features/map/domain/mapDefaults"
import type { LngLat } from "@/features/map/domain/types"
import { cn } from "@workspace/ui/lib/utils"

type MapCanvasProps = PropsWithChildren<{
  onMapClick?: (position: LngLat) => void
  className?: string
}>

const INITIAL_VIEW_STATE = {
  longitude: INITIAL_MAP_CENTER.lng,
  latitude: INITIAL_MAP_CENTER.lat,
  zoom: DEFAULT_MAP_ZOOM,
}

const MAX_BOUNDS = [
  [DELHI_BOUNDS.southWest.lng, DELHI_BOUNDS.southWest.lat],
  [DELHI_BOUNDS.northEast.lng, DELHI_BOUNDS.northEast.lat],
] as [[number, number], [number, number]]

const MapCanvas = memo(
  forwardRef<MapRef, MapCanvasProps>(function MapCanvas(
    { onMapClick, className, children },
    ref
  ) {
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
          initialViewState={INITIAL_VIEW_STATE}
          mapStyle={OPENFREEMAP_STYLE_URL}
          maxBounds={MAX_BOUNDS}
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
)

export default MapCanvas
