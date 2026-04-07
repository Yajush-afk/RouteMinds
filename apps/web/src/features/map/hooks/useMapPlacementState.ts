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
  LocationErrorCode,
  PlaceSuggestion,
} from "@/features/map/domain/types"
import { useUserLocation } from "@/features/map/hooks/useUserLocation"

function getLocationErrorMessage(error: LocationErrorCode | null) {
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

function pointsMatch(first: LngLat, second: LngLat) {
  return first.lat === second.lat && first.lng === second.lng
}

export function useMapPlacementState() {
  const [originPoint, setOriginPoint] = useState<LngLat | null>(null)
  const [destinationPoint, setDestinationPoint] = useState<LngLat | null>(null)
  const [cameraIntent, setCameraIntent] = useState<CameraIntent | null>(null)
  const [placementMessage, setPlacementMessage] = useState<string | null>(null)

  const {
    status,
    error: locationErrorCode,
    position: userPosition,
    locate,
  } = useUserLocation({ autoLocate: true })

  const queueDirectionsCamera = useCallback(
    (
      nextOriginPoint: LngLat | null,
      nextDestinationPoint: LngLat | null,
      fallbackPoint: LngLat
    ) => {
      if (
        nextOriginPoint &&
        nextDestinationPoint &&
        !pointsMatch(nextOriginPoint, nextDestinationPoint)
      ) {
        setCameraIntent({
          type: "fitBounds",
          bounds: {
            southWest: {
              lat: Math.min(nextOriginPoint.lat, nextDestinationPoint.lat),
              lng: Math.min(nextOriginPoint.lng, nextDestinationPoint.lng),
            },
            northEast: {
              lat: Math.max(nextOriginPoint.lat, nextDestinationPoint.lat),
              lng: Math.max(nextOriginPoint.lng, nextDestinationPoint.lng),
            },
          },
          padding: 72,
        })
        return
      }

      setCameraIntent({
        type: "flyTo",
        center: fallbackPoint,
        zoom: DESTINATION_ZOOM,
      })
    },
    []
  )

  const locationMessage = useMemo(() => {
    const userLocationPolicyMessage = userPosition
      ? getLocationRejectionReason(userPosition)
      : null

    return (
      placementMessage ??
      userLocationPolicyMessage ??
      getLocationErrorMessage(locationErrorCode)
    )
  }, [locationErrorCode, placementMessage, userPosition])

  const userLocationPoint = useMemo(() => {
    if (!userPosition) {
      return null
    }

    return getLocationRejectionReason(userPosition) ? null : userPosition
  }, [userPosition])

  useEffect(() => {
    if (!userLocationPoint) {
      return
    }

    if (destinationPoint) {
      return
    }

    if (originPoint && !pointsMatch(originPoint, userLocationPoint)) {
      return
    }

    // Keep auto-geolocation camera behavior without creating/updating route markers.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCameraIntent({
      type: "flyTo",
      center: userLocationPoint,
      zoom: LOCATE_ZOOM,
    })
  }, [
    destinationPoint,
    originPoint,
    queueDirectionsCamera,
    userLocationPoint,
  ])

  useEffect(() => {
    const nextMessage = getLocationErrorMessage(locationErrorCode)

    if (!nextMessage) {
      return
    }

    if (originPoint || destinationPoint) {
      return
    }

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCameraIntent({
      type: "flyTo",
      center: FALLBACK_DELHI_CENTER,
      zoom: DESTINATION_ZOOM,
    })
  }, [destinationPoint, locationErrorCode, originPoint])

  const handleOriginSelect = useCallback(
    (result: PlaceSuggestion) => {
      const rejectionReason = getLocationRejectionReason(result.position)

      if (rejectionReason) {
        setPlacementMessage(rejectionReason)
        return
      }

      setOriginPoint(result.position)
      setPlacementMessage(null)
      queueDirectionsCamera(result.position, destinationPoint, result.position)
    },
    [destinationPoint, queueDirectionsCamera]
  )

  const handleDestinationSelect = useCallback(
    (result: PlaceSuggestion) => {
      const rejectionReason = getLocationRejectionReason(result.position)

      if (rejectionReason) {
        setPlacementMessage(rejectionReason)
        return
      }

      setDestinationPoint(result.position)
      setPlacementMessage(null)
      queueDirectionsCamera(originPoint, result.position, result.position)
    },
    [originPoint, queueDirectionsCamera]
  )

  const handleLocateRequest = useCallback(() => {
    void locate().then((position) => {
      if (!position) {
        return
      }

      if (getLocationRejectionReason(position)) {
        return
      }

      setCameraIntent({
        type: "flyTo",
        center: position,
        zoom: LOCATE_ZOOM,
      })
    })
  }, [locate])

  const handleCameraIntentHandled = useCallback(() => {
    setCameraIntent(null)
  }, [])

  const mapViewportProps = useMemo(
    () => ({
      originPoint,
      showOriginMarker:
        originPoint !== null &&
        (!userLocationPoint || !pointsMatch(originPoint, userLocationPoint)),
      userLocationPoint,
      destinationPoint,
      isLocating: status === "loading",
      locationMessage,
      cameraIntent,
      onCameraIntentHandled: handleCameraIntentHandled,
      onLocateRequest: handleLocateRequest,
    }),
    [
      cameraIntent,
      destinationPoint,
      handleCameraIntentHandled,
      handleLocateRequest,
      locationMessage,
      originPoint,
      status,
      userLocationPoint,
    ]
  )

  return {
    mapViewportProps,
    handleOriginSelect,
    handleDestinationSelect,
  }
}

export default useMapPlacementState
