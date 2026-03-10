import { useEffect, useRef } from "react"
import { useMap } from "react-leaflet"
import type { LatLngTuple } from "leaflet"

import { getBrowserLocation } from "@/lib/geolocation"

type MapAutoLocateProps = {
  onLocateStart: () => void
  onLocateSuccess: (nextPosition: LatLngTuple) => void
  onLocateError: (message: string) => void
}

function MapAutoLocate({
  onLocateStart,
  onLocateSuccess,
  onLocateError,
}: MapAutoLocateProps) {
  const map = useMap()
  const hasRequestedLocation = useRef(false)

  useEffect(() => {
    // StrictMode runs effects twice in development, so we guard this to keep
    // first-load geolocation as a single request.
    if (hasRequestedLocation.current) {
      return
    }

    hasRequestedLocation.current = true

    const locateUser = async () => {
      onLocateStart()

      try {
        const nextPosition = await getBrowserLocation()
        onLocateSuccess(nextPosition)
        map.setView(nextPosition, 15, { animate: true })
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Unable to retrieve your location."

        onLocateError(message)
      }
    }

    void locateUser()
  }, [map, onLocateError, onLocateStart, onLocateSuccess])

  return null
}

export default MapAutoLocate
