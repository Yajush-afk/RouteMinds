import { useEffect, useEffectEvent, useState } from "react"

import {
  DESTINATION_ZOOM,
  FALLBACK_DELHI_CENTER,
  LOCATE_ZOOM,
  YOUR_LOCATION_LABEL,
} from "@/features/map/domain/mapDefaults"
import { getLocationRejectionReason } from "@/features/map/domain/locationPolicy"
import type {
  CameraIntent,
  LngLat,
  LocationErrorCode,
  PlaceSuggestion,
} from "@/features/map/domain/types"
import { useDestinationSearch } from "@/features/map/hooks/useDestinationSearch"
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

export function useMapScreenState() {
  const [selectedPoint, setSelectedPoint] = useState<LngLat | null>(null)
  const [originLabel, setOriginLabel] = useState("")
  const [cameraIntent, setCameraIntent] = useState<CameraIntent | null>(null)
  const [locationMessage, setLocationMessage] = useState<string | null>(null)

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

  const applyUserPosition = useEffectEvent((nextPosition: LngLat) => {
    const rejectionReason = getLocationRejectionReason(nextPosition)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    setSelectedPoint(nextPosition)
    setOriginLabel(YOUR_LOCATION_LABEL)
    setLocationMessage(null)
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
      setSelectedPoint((current) => current ?? FALLBACK_DELHI_CENTER)
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

  function handleLocationChange(nextLocation: string) {
    setOriginLabel(nextLocation)
    setOriginSearchQuery(nextLocation)

    if (!nextLocation.trim()) {
      clearOriginResults()
    }
  }

  function handleOriginFocus() {
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
    const rejectionReason = getLocationRejectionReason(result.position)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    selectOriginSuggestion(result.label)
    setOriginLabel(result.label)
    setSelectedPoint(result.position)
    setLocationMessage(null)
    setCameraIntent({
      type: "flyTo",
      center: result.position,
      zoom: DESTINATION_ZOOM,
    })
  }

  function handleDestinationChange(nextDestination: string) {
    setDestinationSearchQuery(nextDestination)

    if (!nextDestination.trim()) {
      clearDestinationResults()
    }
  }

  function handleDestinationSelect(result: PlaceSuggestion) {
    const rejectionReason = getLocationRejectionReason(result.position)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    selectDestinationSuggestion(result.label)
    setSelectedPoint(result.position)
    setLocationMessage(null)
    setCameraIntent({
      type: "flyTo",
      center: result.position,
      zoom: DESTINATION_ZOOM,
    })
  }

  function handleMapSelect(position: LngLat) {
    const rejectionReason = getLocationRejectionReason(position)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    setSelectedPoint(position)
    setLocationMessage(null)
  }

  function handleMarkerDragEnd(position: LngLat) {
    const rejectionReason = getLocationRejectionReason(position)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    setSelectedPoint(position)
    setLocationMessage(null)
  }

  function handleLocateRequest() {
    void locate()
  }

  function handleCameraIntentHandled() {
    setCameraIntent(null)
  }

  return {
    selectedPoint,
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
    handleDestinationSelect,
    handleMapSelect,
    handleMarkerDragEnd,
    handleLocateRequest,
    handleCameraIntentHandled,
  }
}
