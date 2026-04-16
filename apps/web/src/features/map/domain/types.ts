export type LngLat = {
  lng: number
  lat: number
}

export type LocationField = "from" | "to"

export type PlannerStatus = "idle" | "routing" | "ready" | "partial" | "error"

export type RouteLegStatus = "idle" | "loading" | "ready" | "error"

export type MapViewport = {
  center: LngLat
  zoom: number
}

export type PlaceSuggestion = {
  id: string
  label: string
  position: LngLat
}

export type StopSearchResult = {
  stopId: string
  stopName: string
  position: LngLat
  matchScore: number
}

export type WaypointField = {
  id: string
  query: string
  selectedStop: StopSearchResult | null
}

export type RouteStop = {
  stopId: string
  stopName: string
  position: LngLat
}

export type RouteSegmentPrediction = {
  routeId: string
  fromStopId: string
  toStopId: string
  scheduledDepartureUnix: number | null
  stopSequence: number
  normalizedStopPosition: number
  distanceToPrevStopKm: number
  scheduledSegmentMinutes: number
  waitMinutesBeforeBoarding: number
  predictionSource: "ml" | "scheduled_fallback"
  modelSupported: boolean
  predictedActualSegmentMinutes: number
  predictedSegmentDelayMinutes: number
}

export type RouteLegPlan = {
  id: string
  fromWaypointId: string
  toWaypointId: string
  fromBadge: string
  toBadge: string
  fromStop: StopSearchResult | null
  toStop: StopSearchResult | null
  responseStops: RouteStop[]
  segments: RouteSegmentPrediction[]
  totalEtaMinutes: number
  totalDelayMinutes: number
  waitMinutes: number
  transferCount: number
  status: RouteLegStatus
  errorMessage: string | null
  lineCoordinates: [number, number][]
}

export type RoutePlanSummary = {
  totalEtaMinutes: number
  predictedArrivalUnix: number | null
  totalDelayMinutes: number
  totalWaitMinutes: number
  transferCount: number
}

export type WaypointMarker = {
  id: string
  badge: string
  position: LngLat
  tone: "origin" | "destination" | "waypoint"
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
