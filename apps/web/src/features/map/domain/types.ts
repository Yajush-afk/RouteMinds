export type LngLat = {
  lng: number
  lat: number
}

export type LocationField = "from" | "to"

export type MapViewport = {
  center: LngLat
  zoom: number
}

export type PlaceSuggestion = {
  id: string
  label: string
  position: LngLat
}

export type LocationErrorCode =
  | "UNSUPPORTED"
  | "PERMISSION_DENIED"
  | "POSITION_UNAVAILABLE"
  | "TIMEOUT"
  | "UNKNOWN"

export type LocationState =
  | { status: "idle"; position: null; error: null }
  | { status: "loading"; position: null; error: null }
  | { status: "success"; position: LngLat; error: null }
  | { status: "error"; position: null; error: LocationErrorCode }

export type CameraIntent =
  | {
      type: "flyTo"
      center: LngLat
      zoom?: number
    }
  | {
      type: "easeTo"
      center: LngLat
      zoom?: number
    }
  | {
      type: "fitBounds"
      bounds: {
        southWest: LngLat
        northEast: LngLat
      }
      padding?: number
    }
