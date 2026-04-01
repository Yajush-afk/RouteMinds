import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  DESTINATION_ZOOM,
  FALLBACK_DELHI_CENTER,
  LOCATE_ZOOM,
  YOUR_LOCATION_LABEL,
} from "@/features/map/domain/mapDefaults"
import { getLocationRejectionReason } from "@/features/map/domain/locationPolicy"
import type {
  CameraIntent,
  LocationField,
  LngLat,
  LocationErrorCode,
  PlaceSuggestion,
} from "@/features/map/domain/types"
import { useUserLocation } from "@/features/map/hooks/useUserLocation"
import { reverseGeocode } from "@/features/map/services/places/nominatimPlacesService"

const PINNED_ORIGIN_LABEL = "Selected on map"
const PINNED_DESTINATION_LABEL = "Pinned destination"

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

type UseMapPlacementStateOptions = {
  onFieldLabelChange: (field: LocationField, label: string) => void
}

export function useMapPlacementState({
  onFieldLabelChange,
}: UseMapPlacementStateOptions) {
  const originReverseGeocodeAbortRef = useRef<AbortController | null>(null)
  const destinationReverseGeocodeAbortRef = useRef<AbortController | null>(null)
  const [originPoint, setOriginPoint] = useState<LngLat | null>(null)
  const [destinationPoint, setDestinationPoint] = useState<LngLat | null>(null)
  const [cameraIntent, setCameraIntent] = useState<CameraIntent | null>(null)
  const [locationMessage, setLocationMessage] = useState<string | null>(null)
  const [activeField, setActiveFieldState] = useState<LocationField>("to")

  const {
    status,
    error: locationErrorCode,
    position: userPosition,
    locate,
  } = useUserLocation({ autoLocate: true })

  const cancelReverseGeocode = useCallback((field: LocationField) => {
    const controllerRef =
      field === "from"
        ? originReverseGeocodeAbortRef
        : destinationReverseGeocodeAbortRef

    controllerRef.current?.abort()
    controllerRef.current = null
  }, [])

  const updatePoint = useCallback((field: LocationField, position: LngLat) => {
    if (field === "from") {
      setOriginPoint(position)
      return
    }

    setDestinationPoint(position)
  }, [])

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

  const resolveFieldLabel = useCallback(
    async (field: LocationField, position: LngLat) => {
      cancelReverseGeocode(field)

      const controller = new AbortController()

      if (field === "from") {
        originReverseGeocodeAbortRef.current = controller
      } else {
        destinationReverseGeocodeAbortRef.current = controller
      }

      try {
        const label = await reverseGeocode(position, {
          signal: controller.signal,
          language: "en",
        })

        if (label) {
          onFieldLabelChange(field, label)
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return
        }
      } finally {
        if (field === "from") {
          if (originReverseGeocodeAbortRef.current === controller) {
            originReverseGeocodeAbortRef.current = null
          }
          return
        }

        if (destinationReverseGeocodeAbortRef.current === controller) {
          destinationReverseGeocodeAbortRef.current = null
        }
      }
    },
    [cancelReverseGeocode, onFieldLabelChange]
  )

  const applyMapPlacement = useCallback(
    (field: LocationField, position: LngLat) => {
      const rejectionReason = getLocationRejectionReason(position)

      if (rejectionReason) {
        setLocationMessage(rejectionReason)
        return
      }

      updatePoint(field, position)
      onFieldLabelChange(
        field,
        field === "from" ? PINNED_ORIGIN_LABEL : PINNED_DESTINATION_LABEL
      )
      setLocationMessage(null)
      void resolveFieldLabel(field, position)
    },
    [onFieldLabelChange, resolveFieldLabel, updatePoint]
  )

  useEffect(() => {
    if (!userPosition) {
      return
    }

    const rejectionReason = getLocationRejectionReason(userPosition)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    cancelReverseGeocode("from")
    setOriginPoint(userPosition)
    onFieldLabelChange("from", YOUR_LOCATION_LABEL)
    setLocationMessage(null)

    if (destinationPoint) {
      queueDirectionsCamera(userPosition, destinationPoint, userPosition)
      return
    }

    setCameraIntent({
      type: "flyTo",
      center: userPosition,
      zoom: LOCATE_ZOOM,
    })
  }, [
    cancelReverseGeocode,
    destinationPoint,
    onFieldLabelChange,
    queueDirectionsCamera,
    userPosition,
  ])

  useEffect(() => {
    const nextMessage = getLocationErrorMessage(locationErrorCode)

    if (!nextMessage) {
      return
    }

    setLocationMessage(nextMessage)

    if (originPoint || destinationPoint) {
      return
    }

    setCameraIntent({
      type: "flyTo",
      center: FALLBACK_DELHI_CENTER,
      zoom: DESTINATION_ZOOM,
    })
  }, [destinationPoint, locationErrorCode, originPoint])

  useEffect(() => {
    return () => {
      originReverseGeocodeAbortRef.current?.abort()
      destinationReverseGeocodeAbortRef.current?.abort()
    }
  }, [])

  const setActiveField = useCallback((field: LocationField) => {
    setActiveFieldState(field)
  }, [])

  const handleOriginSelect = useCallback(
    (result: PlaceSuggestion) => {
      cancelReverseGeocode("from")

      const rejectionReason = getLocationRejectionReason(result.position)

      if (rejectionReason) {
        setLocationMessage(rejectionReason)
        return
      }

      setActiveFieldState("from")
      setOriginPoint(result.position)
      setLocationMessage(null)
      queueDirectionsCamera(result.position, destinationPoint, result.position)
    },
    [cancelReverseGeocode, destinationPoint, queueDirectionsCamera]
  )

  const handleDestinationSelect = useCallback(
    (result: PlaceSuggestion) => {
      cancelReverseGeocode("to")

      const rejectionReason = getLocationRejectionReason(result.position)

      if (rejectionReason) {
        setLocationMessage(rejectionReason)
        return
      }

      setActiveFieldState("to")
      setDestinationPoint(result.position)
      setLocationMessage(null)
      queueDirectionsCamera(originPoint, result.position, result.position)
    },
    [cancelReverseGeocode, originPoint, queueDirectionsCamera]
  )

  const handleMapSelect = useCallback(
    (position: LngLat) => {
      applyMapPlacement(activeField, position)
    },
    [activeField, applyMapPlacement]
  )

  const handleOriginMarkerDragEnd = useCallback(
    (position: LngLat) => {
      setActiveFieldState("from")
      applyMapPlacement("from", position)
    },
    [applyMapPlacement]
  )

  const handleDestinationMarkerDragEnd = useCallback(
    (position: LngLat) => {
      setActiveFieldState("to")
      applyMapPlacement("to", position)
    },
    [applyMapPlacement]
  )

  const handleLocateRequest = useCallback(() => {
    void locate()
  }, [locate])

  const handleCameraIntentHandled = useCallback(() => {
    setCameraIntent(null)
  }, [])

  const mapViewportProps = useMemo(
    () => ({
      originPoint,
      destinationPoint,
      isLocating: status === "loading",
      locationMessage,
      cameraIntent,
      onMapClick: handleMapSelect,
      onOriginMarkerDragEnd: handleOriginMarkerDragEnd,
      onDestinationMarkerDragEnd: handleDestinationMarkerDragEnd,
      onCameraIntentHandled: handleCameraIntentHandled,
      onLocateRequest: handleLocateRequest,
    }),
    [
      cameraIntent,
      destinationPoint,
      handleCameraIntentHandled,
      handleDestinationMarkerDragEnd,
      handleLocateRequest,
      handleMapSelect,
      handleOriginMarkerDragEnd,
      locationMessage,
      originPoint,
      status,
    ]
  )

  return {
    mapViewportProps,
    setActiveField,
    handleOriginSelect,
    handleDestinationSelect,
  }
}

export default useMapPlacementState
