import { useCallback, useEffect, useMemo, useState } from "react"

import {
  DESTINATION_ZOOM,
  FALLBACK_DELHI_CENTER,
  LOCATE_ZOOM,
} from "@/features/map/domain/mapDefaults"
import { getLocationRejectionReason } from "@/features/map/domain/locationPolicy"
import type {
  CameraIntent,
  LngLat,
  PlannerStatus,
  RouteLegPlan,
  RoutePlanSummary,
  StopSearchResult,
  WaypointField,
  WaypointMarker,
} from "@/features/map/domain/types"
import { useUserLocation } from "@/features/map/hooks/useUserLocation"
import { optimizeRoute } from "@/features/map/services/routes/routePlannerService"

const DEFAULT_WAYPOINT_COUNT = 2
const MAX_WAYPOINT_COUNT = 8

function getLocationErrorMessage(error: string | null) {
  switch (error) {
    case "UNSUPPORTED":
      return "Geolocation is not supported by this browser."
    case "PERMISSION_DENIED":
      return "Location access was denied."
    case "POSITION_UNAVAILABLE":
      return "Your location is currently unavailable."
    case "TIMEOUT":
      return "Location request timed out."
    case "UNKNOWN":
      return "Unable to retrieve your location."
    default:
      return null
  }
}

function getWaypointBadge(index: number) {
  return String.fromCharCode(65 + index)
}

function createWaypoint(id: string): WaypointField {
  return {
    id,
    query: "",
    selectedStop: null,
  }
}

function createInitialWaypoints() {
  return Array.from({ length: DEFAULT_WAYPOINT_COUNT }, () =>
    createWaypoint(crypto.randomUUID())
  )
}

function moveWaypointInList(
  currentWaypoints: WaypointField[],
  waypointId: string,
  direction: -1 | 1
) {
  const currentIndex = currentWaypoints.findIndex(
    (waypoint) => waypoint.id === waypointId
  )

  if (currentIndex < 0) {
    return currentWaypoints
  }

  const nextIndex = currentIndex + direction
  if (nextIndex < 0 || nextIndex >= currentWaypoints.length) {
    return currentWaypoints
  }

  const nextWaypoints = [...currentWaypoints]
  const [movedWaypoint] = nextWaypoints.splice(currentIndex, 1)
  nextWaypoints.splice(nextIndex, 0, movedWaypoint)
  return nextWaypoints
}

function toBounds(points: LngLat[]) {
  const [firstPoint, ...rest] = points

  return rest.reduce(
    (bounds, point) => ({
      southWest: {
        lat: Math.min(bounds.southWest.lat, point.lat),
        lng: Math.min(bounds.southWest.lng, point.lng),
      },
      northEast: {
        lat: Math.max(bounds.northEast.lat, point.lat),
        lng: Math.max(bounds.northEast.lng, point.lng),
      },
    }),
    {
      southWest: { ...firstPoint },
      northEast: { ...firstPoint },
    }
  )
}

function createIdleRouteLeg(
  waypoints: WaypointField[],
  index: number,
  status: RouteLegPlan["status"] = "idle"
): RouteLegPlan {
  const fromWaypoint = waypoints[index]
  const toWaypoint = waypoints[index + 1]

  return {
    id: `${fromWaypoint.id}:${toWaypoint.id}`,
    fromWaypointId: fromWaypoint.id,
    toWaypointId: toWaypoint.id,
    fromBadge: getWaypointBadge(index),
    toBadge: getWaypointBadge(index + 1),
    fromStop: fromWaypoint.selectedStop,
    toStop: toWaypoint.selectedStop,
    responseStops: [],
    segments: [],
    totalEtaMinutes: 0,
    totalDelayMinutes: 0,
    waitMinutes: 0,
    status,
    errorMessage: null,
    lineCoordinates: [],
  }
}

function getTransferCount(routeLegs: RouteLegPlan[]) {
  let previousRouteId: string | null = null
  let transferCount = 0

  for (const leg of routeLegs) {
    for (const segment of leg.segments) {
      if (previousRouteId !== null && previousRouteId !== segment.routeId) {
        transferCount += 1
      }

      previousRouteId = segment.routeId
    }
  }

  return transferCount
}

export function useMultiStopRoutePlanner() {
  const [waypoints, setWaypoints] = useState<WaypointField[]>(createInitialWaypoints)
  const [routeWaypoints, setRouteWaypoints] = useState<WaypointField[]>(waypoints)
  const [manualCameraIntent, setManualCameraIntent] = useState<CameraIntent | null>(
    null
  )
  const [routingResult, setRoutingResult] = useState<{
    requestKey: string
    legs: RouteLegPlan[]
    queryTimestampUnix: number | null
    status: Extract<PlannerStatus, "ready" | "partial" | "error">
  }>({
    requestKey: "",
    legs: [],
    queryTimestampUnix: null,
    status: "ready",
  })

  const {
    status: locationStatus,
    error: locationErrorCode,
    position: userPosition,
    locate,
  } = useUserLocation({ autoLocate: true })

  const userLocationPoint = useMemo(() => {
    if (!userPosition) {
      return null
    }

    return getLocationRejectionReason(userPosition) ? null : userPosition
  }, [userPosition])

  const waypointMarkers = useMemo<WaypointMarker[]>(() => {
    const selectedWaypointIndices = routeWaypoints.flatMap((waypoint, index) =>
      waypoint.selectedStop ? [index] : []
    )

    return selectedWaypointIndices.map((waypointIndex, selectedIndex) => {
      const waypoint = routeWaypoints[waypointIndex]

      return {
        id: waypoint.id,
        badge: getWaypointBadge(waypointIndex),
        position: waypoint.selectedStop!.position,
        tone:
          selectedIndex === 0
            ? "origin"
            : selectedIndex === selectedWaypointIndices.length - 1
              ? "destination"
            : "waypoint",
      }
    })
  }, [routeWaypoints])

  const baseLegs = useMemo(
    () =>
      routeWaypoints.slice(0, -1).map((_, index) => {
        const fromStop = routeWaypoints[index].selectedStop
        const toStop = routeWaypoints[index + 1].selectedStop

        return createIdleRouteLeg(
          routeWaypoints,
          index,
          fromStop && toStop ? "loading" : "idle"
        )
      }),
    [routeWaypoints]
  )

  const hasSelectedLeg = useMemo(
    () => baseLegs.some((leg) => leg.fromStop && leg.toStop),
    [baseLegs]
  )

  const selectedLegRequestKey = useMemo(
    () =>
      baseLegs
        .map((leg) =>
          `${leg.fromWaypointId}:${leg.fromStop?.stopId ?? ""}->${leg.toWaypointId}:${leg.toStop?.stopId ?? ""}`
        )
        .join("|"),
    [baseLegs]
  )

  useEffect(() => {
    let isActive = true
    const controller = new AbortController()

    if (!hasSelectedLeg) {
      return () => {
        controller.abort()
      }
    }

    const startedAtUnix = Math.floor(Date.now() / 1000)
    async function planRoutes() {
      let cursorTimestampUnix = startedAtUnix
      let sawReadyLeg = false
      let sawErroredLeg = false
      const nextLegs: RouteLegPlan[] = []

      for (const baseLeg of baseLegs) {
        if (!baseLeg.fromStop || !baseLeg.toStop) {
          nextLegs.push({
            ...baseLeg,
            status: "idle",
          })
          continue
        }

        if (baseLeg.fromStop.stopId === baseLeg.toStop.stopId) {
          sawReadyLeg = true
          nextLegs.push({
            ...baseLeg,
            status: "ready",
            responseStops: [
              {
                stopId: baseLeg.fromStop.stopId,
                stopName: baseLeg.fromStop.stopName,
                position: baseLeg.fromStop.position,
              },
            ],
          })
          continue
        }

        try {
          const result = await optimizeRoute(
            baseLeg.fromStop.stopId,
            baseLeg.toStop.stopId,
            cursorTimestampUnix,
            { signal: controller.signal }
          )

          sawReadyLeg = true
          cursorTimestampUnix += Math.round(result.totalPredictedEtaMinutes * 60)

          nextLegs.push({
            ...baseLeg,
            responseStops: result.stops,
            segments: result.segments,
            totalEtaMinutes: result.totalPredictedEtaMinutes,
            totalDelayMinutes: result.segments.reduce(
              (total, segment) =>
                total + segment.predictedSegmentDelayMinutes,
              0
            ),
            waitMinutes: result.segments.reduce(
              (total, segment) =>
                total + segment.waitMinutesBeforeBoarding,
              0
            ),
            status: "ready",
            lineCoordinates: [
              ...(result.stops[0]?.stopId !== baseLeg.fromStop.stopId
                ? [[baseLeg.fromStop.position.lng, baseLeg.fromStop.position.lat] as [
                    number,
                    number,
                  ]]
                : []),
              ...result.stops.map((stop) => [
                stop.position.lng,
                stop.position.lat,
              ] as [number, number]),
              ...(result.stops[result.stops.length - 1]?.stopId !== baseLeg.toStop.stopId
                ? [[baseLeg.toStop.position.lng, baseLeg.toStop.position.lat] as [
                    number,
                    number,
                  ]]
                : []),
            ],
          })
        } catch (error) {
          if (
            error instanceof DOMException &&
            error.name === "AbortError"
          ) {
            return
          }

          sawErroredLeg = true
          nextLegs.push({
            ...baseLeg,
            status: "error",
            errorMessage:
              error instanceof Error
                ? error.message
                : "Unable to draw this route leg.",
          })
        }
      }

      if (!isActive) {
        return
      }

      setRoutingResult({
        requestKey: selectedLegRequestKey,
        legs: nextLegs,
        queryTimestampUnix: startedAtUnix,
        status:
          sawReadyLeg && sawErroredLeg
            ? "partial"
            : sawErroredLeg
              ? "error"
              : "ready",
      })
    }

    void planRoutes()

    return () => {
      isActive = false
      controller.abort()
    }
  }, [baseLegs, hasSelectedLeg, selectedLegRequestKey])

  const routeLegs = useMemo(() => {
    if (!hasSelectedLeg) {
      return baseLegs.map((leg) => ({
        ...leg,
        status: "idle" as const,
      }))
    }

    if (routingResult.requestKey !== selectedLegRequestKey) {
      return baseLegs
    }

    return routingResult.legs
  }, [baseLegs, hasSelectedLeg, routingResult, selectedLegRequestKey])

  const plannerStatus = useMemo<PlannerStatus>(() => {
    if (!hasSelectedLeg) {
      return "idle"
    }

    if (routingResult.requestKey !== selectedLegRequestKey) {
      return "routing"
    }

    return routingResult.status
  }, [hasSelectedLeg, routingResult, selectedLegRequestKey])

  const summary = useMemo<RoutePlanSummary | null>(() => {
    const readyLegs = routeLegs.filter((leg) => leg.status === "ready")

    if (
      readyLegs.length === 0 ||
      routingResult.requestKey !== selectedLegRequestKey ||
      routingResult.queryTimestampUnix === null
    ) {
      return null
    }

    const totalEtaMinutes = readyLegs.reduce(
      (total, leg) => total + leg.totalEtaMinutes,
      0
    )
    const totalDelayMinutes = readyLegs.reduce(
      (total, leg) => total + leg.totalDelayMinutes,
      0
    )
    const totalWaitMinutes = readyLegs.reduce(
      (total, leg) => total + leg.waitMinutes,
      0
    )

    return {
      totalEtaMinutes,
      predictedArrivalUnix:
        routingResult.queryTimestampUnix + Math.round(totalEtaMinutes * 60),
      totalDelayMinutes,
      totalWaitMinutes,
      transferCount: getTransferCount(readyLegs),
    }
  }, [routeLegs, routingResult, selectedLegRequestKey])

  const automaticCameraIntent = useMemo<CameraIntent | null>(() => {
    const points = [
      ...routeWaypoints
        .map((waypoint) => waypoint.selectedStop?.position ?? null)
        .filter((point): point is LngLat => point !== null),
      ...routeLegs.flatMap((leg) =>
        leg.lineCoordinates.map(([lng, lat]) => ({ lng, lat }))
      ),
    ]

    if (points.length === 0) {
      if (userLocationPoint) {
        return {
          type: "flyTo" as const,
          center: userLocationPoint,
          zoom: LOCATE_ZOOM,
        }
      }

      if (getLocationErrorMessage(locationErrorCode)) {
        return {
          type: "flyTo" as const,
          center: FALLBACK_DELHI_CENTER,
          zoom: DESTINATION_ZOOM,
        }
      }

      return null
    }

    if (points.length === 1) {
      return {
        type: "flyTo",
        center: points[0],
        zoom: DESTINATION_ZOOM,
      }
    }

    return {
      type: "fitBounds",
      bounds: toBounds(points),
      padding: 60,
    }
  }, [
    locationErrorCode,
    routeLegs,
    routeWaypoints,
    userLocationPoint,
  ])

  const cameraIntent = manualCameraIntent ?? automaticCameraIntent

  const locationMessage = useMemo(() => {
    if (waypointMarkers.length > 0) {
      return null
    }

    const userLocationPolicyMessage = userPosition
      ? getLocationRejectionReason(userPosition)
      : null

    return userLocationPolicyMessage ?? getLocationErrorMessage(locationErrorCode)
  }, [locationErrorCode, userPosition, waypointMarkers.length])

  const handleLocateRequest = useCallback(() => {
    void locate().then((position) => {
      if (!position) {
        return
      }

      if (getLocationRejectionReason(position)) {
        return
      }

      setManualCameraIntent({
        type: "flyTo",
        center: position,
        zoom: LOCATE_ZOOM,
      })
    })
  }, [locate])

  const handleCameraIntentHandled = useCallback(() => {
    setManualCameraIntent(null)
  }, [])

  const updateWaypointQuery = useCallback((waypointId: string, query: string) => {
    setWaypoints((currentWaypoints) =>
      currentWaypoints.map((waypoint) =>
        waypoint.id !== waypointId
          ? waypoint
          : {
              ...waypoint,
              query,
              selectedStop:
                waypoint.selectedStop?.stopName === query
                  ? waypoint.selectedStop
                  : null,
            }
      )
    )

    setRouteWaypoints((currentWaypoints) =>
      currentWaypoints.map((waypoint) =>
        waypoint.id !== waypointId
          ? waypoint
          : waypoint.selectedStop?.stopName === query
            ? waypoint
            : {
                ...waypoint,
                selectedStop: null,
              }
      )
    )
  }, [])

  const selectWaypointStop = useCallback(
    (waypointId: string, stop: StopSearchResult) => {
      setWaypoints((currentWaypoints) =>
        currentWaypoints.map((waypoint) =>
          waypoint.id !== waypointId
            ? waypoint
            : {
                ...waypoint,
                query: stop.stopName,
                selectedStop: stop,
            }
        )
      )

      setRouteWaypoints((currentWaypoints) =>
        currentWaypoints.map((waypoint) =>
          waypoint.id !== waypointId
            ? waypoint
            : {
                ...waypoint,
                query: stop.stopName,
                selectedStop: stop,
              }
        )
      )
    },
    []
  )

  const clearWaypoint = useCallback((waypointId: string) => {
    setWaypoints((currentWaypoints) =>
      currentWaypoints.map((waypoint) =>
        waypoint.id !== waypointId
          ? waypoint
          : {
              ...waypoint,
              query: "",
              selectedStop: null,
          }
      )
    )

    setRouteWaypoints((currentWaypoints) =>
      currentWaypoints.map((waypoint) =>
        waypoint.id !== waypointId
          ? waypoint
          : {
              ...waypoint,
              query: "",
              selectedStop: null,
            }
      )
    )
  }, [])

  const addWaypoint = useCallback(() => {
    const nextWaypoint = createWaypoint(crypto.randomUUID())

    setWaypoints((currentWaypoints) => {
      if (currentWaypoints.length >= MAX_WAYPOINT_COUNT) {
        return currentWaypoints
      }

      return [...currentWaypoints, nextWaypoint]
    })

    setRouteWaypoints((currentWaypoints) => {
      if (currentWaypoints.length >= MAX_WAYPOINT_COUNT) {
        return currentWaypoints
      }

      return [...currentWaypoints, nextWaypoint]
    })
  }, [])

  const removeWaypoint = useCallback((waypointId: string) => {
    setWaypoints((currentWaypoints) => {
      if (currentWaypoints.length <= DEFAULT_WAYPOINT_COUNT) {
        return currentWaypoints
      }

      return currentWaypoints.filter((waypoint) => waypoint.id !== waypointId)
    })

    setRouteWaypoints((currentWaypoints) => {
      if (currentWaypoints.length <= DEFAULT_WAYPOINT_COUNT) {
        return currentWaypoints
      }

      return currentWaypoints.filter((waypoint) => waypoint.id !== waypointId)
    })
  }, [])

  const moveWaypoint = useCallback((waypointId: string, direction: -1 | 1) => {
    setWaypoints((currentWaypoints) =>
      moveWaypointInList(currentWaypoints, waypointId, direction)
    )
    setRouteWaypoints((currentWaypoints) =>
      moveWaypointInList(currentWaypoints, waypointId, direction)
    )
  }, [])

  const clearTrip = useCallback(() => {
    setWaypoints((currentWaypoints) =>
      currentWaypoints
        .slice(0, DEFAULT_WAYPOINT_COUNT)
        .map((waypoint) => ({
          ...waypoint,
          query: "",
          selectedStop: null,
        }))
    )

    setRouteWaypoints((currentWaypoints) =>
      currentWaypoints
        .slice(0, DEFAULT_WAYPOINT_COUNT)
        .map((waypoint) => ({
          ...waypoint,
          query: "",
          selectedStop: null,
        }))
    )
  }, [])

  return {
    sidebarProps: {
      waypoints,
      routeLegs,
      summary,
      plannerStatus,
      canAddWaypoint: waypoints.length < MAX_WAYPOINT_COUNT,
      onWaypointQueryChange: updateWaypointQuery,
      onWaypointSelect: selectWaypointStop,
      onWaypointClear: clearWaypoint,
      onWaypointRemove: removeWaypoint,
      onWaypointMoveUp: (waypointId: string) => moveWaypoint(waypointId, -1),
      onWaypointMoveDown: (waypointId: string) => moveWaypoint(waypointId, 1),
      onAddWaypoint: addWaypoint,
      onClearTrip: clearTrip,
    },
    mapViewportProps: {
      waypointMarkers,
      routeLegs,
      userLocationPoint,
      isLocating: locationStatus === "loading",
      locationMessage,
      cameraIntent,
      onLocateRequest: handleLocateRequest,
      onCameraIntentHandled: handleCameraIntentHandled,
    },
  }
}

export default useMultiStopRoutePlanner
