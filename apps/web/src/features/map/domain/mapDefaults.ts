import { DELHI_POLYGON_LNGLAT } from "@/data/delhi-polygon"
import type { LngLat } from "./types"

function getDelhiBounds() {
  const [firstLng, firstLat] = DELHI_POLYGON_LNGLAT[0]

  const bounds = DELHI_POLYGON_LNGLAT.slice(1).reduce(
    (currentBounds, [lng, lat]) => ({
      southWest: {
        lng: Math.min(currentBounds.southWest.lng, lng),
        lat: Math.min(currentBounds.southWest.lat, lat),
      },
      northEast: {
        lng: Math.max(currentBounds.northEast.lng, lng),
        lat: Math.max(currentBounds.northEast.lat, lat),
      },
    }),
    {
      southWest: { lng: firstLng, lat: firstLat },
      northEast: { lng: firstLng, lat: firstLat },
    }
  )

  const padding = 0.015

  return {
    southWest: {
      lng: bounds.southWest.lng - padding,
      lat: bounds.southWest.lat - padding,
    },
    northEast: {
      lng: bounds.northEast.lng + padding,
      lat: bounds.northEast.lat + padding,
    },
  } as const
}

export const DELHI_BOUNDS = getDelhiBounds()

export const INITIAL_MAP_CENTER: LngLat = {
  lat: 28.6139,
  lng: 77.209,
}

export const FALLBACK_DELHI_CENTER: LngLat = {
  lat: 28.6139,
  lng: 77.209,
}

export const DEFAULT_MAP_ZOOM = 13
export const MIN_MAP_ZOOM = 10
export const LOCATE_ZOOM = 17
export const DESTINATION_ZOOM = 14

export const DELHI_ONLY_ALERT_MESSAGE =
  "RouteMinds is only limited to Delhi for now."

export const YOUR_LOCATION_LABEL = "Your Location"

export const DESTINATION_SEARCH_DEBOUNCE_MS = 350
