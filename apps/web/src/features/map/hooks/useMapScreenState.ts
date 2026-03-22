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
    searchQuery,
    setSearchQuery,
    results,
    isSearching,
    hasAttempted,
    clearResults,
    selectSuggestion,
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
  }

  function handleDestinationChange(nextDestination: string) {
    setSearchQuery(nextDestination)

    if (!nextDestination.trim()) {
      clearResults()
    }
  }

  function handleDestinationSelect(result: PlaceSuggestion) {
    const rejectionReason = getLocationRejectionReason(result.position)

    if (rejectionReason) {
      setLocationMessage(rejectionReason)
      return
    }

    selectSuggestion(result.label)
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
    destinationText: searchQuery,
    destinationResults: results,
    isDestinationSearching: isSearching,
    showNoDestinationResults:
      hasAttempted && searchQuery.trim().length >= 3 && results.length === 0,
    isLocating: status === "loading",
    locationMessage,
    cameraIntent,
    handleLocationChange,
    handleDestinationChange,
    handleDestinationSelect,
    handleMapSelect,
    handleMarkerDragEnd,
    handleLocateRequest,
    handleCameraIntentHandled,
  }
}
