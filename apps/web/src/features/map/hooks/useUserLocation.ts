import { useCallback, useEffect, useRef, useState } from "react"

import type {
  LngLat,
  LocationErrorCode,
  LocationState,
} from "@/features/map/domain/types"

import {
  BrowserLocationError,
  getCurrentPosition,
} from "@/features/map/services/location/browserLocationService"

type UseUserLocationOptions = {
  autoLocate?: boolean
}

type UseUserLocationResult = {
  status: LocationState["status"]
  error: LocationErrorCode | null
  position: LngLat | null
  locate: () => Promise<LngLat | null>
  hasAutoLocated: boolean
}

const IDLE_STATE: LocationState = {
  status: "idle",
  position: null,
  error: null,
}

export function useUserLocation(
  options: UseUserLocationOptions = {}
): UseUserLocationResult {
  const { autoLocate = false } = options
  const hasRequestedAutoLocateRef = useRef(false)
  const [locationState, setLocationState] = useState<LocationState>(IDLE_STATE)

  const locate = useCallback(async (): Promise<LngLat | null> => {
    setLocationState({
      status: "loading",
      position: null,
      error: null,
    })

    try {
      const position = await getCurrentPosition()

      setLocationState({
        status: "success",
        position,
        error: null,
      })

      return position
    } catch (error) {
      const errorCode =
        error instanceof BrowserLocationError ? error.code : "UNKNOWN"

      setLocationState({
        status: "error",
        position: null,
        error: errorCode,
      })

      return null
    }
  }, [])

  useEffect(() => {
    if (!autoLocate || hasRequestedAutoLocateRef.current) {
      return
    }

    hasRequestedAutoLocateRef.current = true
    queueMicrotask(() => {
      void locate()
    })
  }, [autoLocate, locate])

  return {
    status: locationState.status,
    error: locationState.error,
    position: locationState.position,
    locate,
    hasAutoLocated: autoLocate && locationState.status !== "idle",
  }
}

export default useUserLocation
