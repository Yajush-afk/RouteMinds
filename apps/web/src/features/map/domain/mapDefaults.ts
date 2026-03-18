import type { LngLat } from "./types"

export const INDIA_BOUNDS = {
  southWest: { lat: 6.5, lng: 68.0 },
  northEast: { lat: 37.6, lng: 97.5 },
} as const

export const INITIAL_MAP_CENTER: LngLat = {
  lat: 22.9734,
  lng: 78.6569,
}

export const FALLBACK_DELHI_CENTER: LngLat = {
  lat: 28.6139,
  lng: 77.209,
}

export const DEFAULT_MAP_ZOOM = 13
export const MIN_MAP_ZOOM = 5
export const LOCATE_ZOOM = 20
export const DESTINATION_ZOOM = 14

export const DELHI_ONLY_ALERT_MESSAGE =
  "RouteMinds is only limited to Delhi for now."

export const YOUR_LOCATION_LABEL = "Your Location"

export const DESTINATION_SEARCH_DEBOUNCE_MS = 350
