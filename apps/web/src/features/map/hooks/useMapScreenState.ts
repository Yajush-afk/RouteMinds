import { useEffect, useEffectEvent, useRef, useState } from "react"

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
import { useDestinationSearch } from "@/features/map/hooks/useDestinationSearch"
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

export function useMapScreenState() {
  const originReverseGeocodeAbortRef = useRef<AbortController | null>(null)
  const destinationReverseGeocodeAbortRef = useRef<AbortController | null>(null)
  const [originPoint, setOriginPoint] = useState<LngLat | null>(null)
  const [destinationPoint, setDestinationPoint] = useState<LngLat | null>(null)
  const [originLabel, setOriginLabel] = useState("")
  const [cameraIntent, setCameraIntent] = useState<CameraIntent | null>(null)
  const [locationMessage, setLocationMessage] = useState<string | null>(null)
  const [activeField, setActiveField] = useState<LocationField>("to")

  const {
    status,
    error: locationErrorCode,
    position: userPosition,
    locate,
  } = useUserLocation({ autoLocate: true })

  const {
    searchQuery: originSearchQuery,
    setSearchQuery: setOriginSearchQuery,
    results: originResults,
    isSearching: isOriginSearching,
    hasAttempted: hasOriginAttempted,
    clearResults: clearOriginResults,
    selectSuggestion: selectOriginSuggestion,
  } = useDestinationSearch()

  const {
    searchQuery: destinationSearchQuery,
    setSearchQuery: setDestinationSearchQuery,
    results: destinationResults,
    isSearching: isDestinationSearching,
    hasAttempted: hasDestinationAttempted,
    clearResults: clearDestinationResults,
    selectSuggestion: selectDestinationSuggestion,
  } = useDestinationSearch()

  const mapCenter = destinationPoint ?? originPoint

  function cancelReverseGeocode(field: LocationField) {
    const controllerRef =
      field === "from"
        ? originReverseGeocodeAbortRef
        : destinationReverseGeocodeAbortRef

    controllerRef.current?.abort()
    controllerRef.current = null
  }

  function syncFieldLabel(field: LocationField, nextLabel: string) {
    if (field === "from") {
      setOriginLabel(nextLabel)
      selectOriginSuggestion(nextLabel)
      return
    }

    selectDestinationSuggestion(nextLabel)
  }

  function updatePoint(field: LocationField, position: LngLat) {
    if (field === "from") {
      setOriginPoint(position)
      return
    }

    setDestinationPoint(position)
  }

  const queueDirectionsCamera = useEffectEvent(
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
    }
  )

  const resolveFieldLabel = useEffectEvent(
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

        if (!label) {
          return
        }

        syncFieldLabel(field, label)
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
    }
  )

  const applyMapPlacement = useEffectEvent(
    (field: LocationField, position: LngLat) => {
      const rejectionReason = getLocationRejectionReason(position)

      if (rejectionReason) {
        setLocationMessage(rejectionReason)
        return
      }

      updatePoint(field, position)
      syncFieldLabel(
        field,
        field === "from" ? PINNED_ORIGIN_LABEL : PINNED_DESTINATION_LABEL
      )
      setLocationMessage(null)
      void resolveFieldLabel(field, position)
    }
  )

  const applyUserPosition = useEffectEvent((nextPosition: LngLat) => {
    const rejectionReason = getLocationRejectionReason(nextPosition)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    cancelReverseGeocode("from")
    setOriginPoint(nextPosition)
    setOriginLabel(YOUR_LOCATION_LABEL)
    setOriginSearchQuery("")
    clearOriginResults()
    setLocationMessage(null)

    if (destinationPoint) {
      queueDirectionsCamera(nextPosition, destinationPoint, nextPosition)
      return
    }

    setCameraIntent({
      type: "flyTo",
      center: nextPosition,
      zoom: LOCATE_ZOOM,
    })
  })

  const applyLocationError = useEffectEvent(
    (nextLocationErrorCode: LocationErrorCode | null) => {
      const nextMessage = getLocationErrorMessage(nextLocationErrorCode)

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
    }
  )

  useEffect(() => {
    if (!userPosition) {
      return
    }

    applyUserPosition(userPosition)
  }, [userPosition])

  useEffect(() => {
    applyLocationError(locationErrorCode)
  }, [locationErrorCode])

  useEffect(() => {
    return () => {
      originReverseGeocodeAbortRef.current?.abort()
      destinationReverseGeocodeAbortRef.current?.abort()
    }
  }, [])

  function handleLocationChange(nextLocation: string) {
    cancelReverseGeocode("from")
    setActiveField("from")
    setOriginLabel(nextLocation)
    setOriginSearchQuery(nextLocation)

    if (!nextLocation.trim()) {
      clearOriginResults()
    }
  }

  function handleOriginFocus() {
    setActiveField("from")

    if (originLabel === YOUR_LOCATION_LABEL) {
      setOriginLabel("")
      setOriginSearchQuery("")
      clearOriginResults()
    }
  }

  function handleOriginBlur() {
    if (originLabel.trim()) {
      return
    }

    setOriginLabel(YOUR_LOCATION_LABEL)
    setOriginSearchQuery("")
    clearOriginResults()
  }

  function handleOriginSelect(result: PlaceSuggestion) {
    cancelReverseGeocode("from")

    const rejectionReason = getLocationRejectionReason(result.position)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    setActiveField("from")
    selectOriginSuggestion(result.label)
    setOriginLabel(result.label)
    setOriginPoint(result.position)
    setLocationMessage(null)
    queueDirectionsCamera(result.position, destinationPoint, result.position)
  }

  function handleDestinationChange(nextDestination: string) {
    cancelReverseGeocode("to")
    setActiveField("to")
    setDestinationSearchQuery(nextDestination)

    if (!nextDestination.trim()) {
      clearDestinationResults()
    }
  }

  function handleDestinationFocus() {
    setActiveField("to")
  }

  function handleDestinationSelect(result: PlaceSuggestion) {
    cancelReverseGeocode("to")

    const rejectionReason = getLocationRejectionReason(result.position)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    setActiveField("to")
    selectDestinationSuggestion(result.label)
    setDestinationPoint(result.position)
    setLocationMessage(null)
    queueDirectionsCamera(originPoint, result.position, result.position)
  }

  function handleMapSelect(position: LngLat) {
    applyMapPlacement(activeField, position)
  }

  function handleOriginMarkerDragEnd(position: LngLat) {
    setActiveField("from")
    applyMapPlacement("from", position)
  }

  function handleDestinationMarkerDragEnd(position: LngLat) {
    setActiveField("to")
    applyMapPlacement("to", position)
  }

  function handleLocateRequest() {
    void locate()
  }

  function handleCameraIntentHandled() {
    setCameraIntent(null)
  }

  return {
    mapCenter,
    originPoint,
    destinationPoint,
    originLabel,
    originResults,
    isOriginSearching,
    showNoOriginResults:
      hasOriginAttempted &&
      originSearchQuery.trim().length >= 3 &&
      originResults.length === 0,
    destinationText: destinationSearchQuery,
    destinationResults,
    isDestinationSearching,
    showNoDestinationResults:
      hasDestinationAttempted &&
      destinationSearchQuery.trim().length >= 3 &&
      destinationResults.length === 0,
    isLocating: status === "loading",
    locationMessage,
    cameraIntent,
    handleLocationChange,
    handleOriginFocus,
    handleOriginBlur,
    handleOriginSelect,
    handleDestinationChange,
    handleDestinationFocus,
    handleDestinationSelect,
    handleMapSelect,
    handleOriginMarkerDragEnd,
    handleDestinationMarkerDragEnd,
    handleLocateRequest,
    handleCameraIntentHandled,
  }
}
