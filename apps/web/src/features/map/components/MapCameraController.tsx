import { useEffect } from "react"
import type { RefObject } from "react"
import type { MapRef } from "react-map-gl/maplibre"

import type { CameraIntent } from "@/features/map/domain/types"

type MapCameraControllerProps = {
  mapRef: RefObject<MapRef | null>
  intent: CameraIntent | null
  onHandled?: () => void
}

function MapCameraController({
  mapRef,
  intent,
  onHandled,
}: MapCameraControllerProps) {
  useEffect(() => {
    if (!intent || !mapRef.current) {
      return
    }

    const map = mapRef.current

    switch (intent.type) {
      case "flyTo":
        map.flyTo({
          center: [intent.center.lng, intent.center.lat],
          zoom: intent.zoom,
          essential: true,
        })
        break

      case "easeTo":
        map.easeTo({
          center: [intent.center.lng, intent.center.lat],
          zoom: intent.zoom,
          essential: true,
        })
        break

      case "fitBounds":
        map.fitBounds(
          [
            [intent.bounds.southWest.lng, intent.bounds.southWest.lat],
            [intent.bounds.northEast.lng, intent.bounds.northEast.lat],
          ],
          {
            padding: intent.padding ?? 48,
            duration: 800,
          }
        )
        break
    }

    onHandled?.()
  }, [intent, mapRef, onHandled])

  return null
}

export default MapCameraController
