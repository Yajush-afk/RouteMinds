import { Marker } from "react-map-gl/maplibre"
import type { MarkerDragEvent } from "react-map-gl/maplibre"

import type { LngLat } from "@/features/map/domain/types"

type SelectedLocationMarkerProps = {
  position: LngLat
  onDragEnd: (position: LngLat) => void
}

function SelectedLocationMarker({
  position,
  onDragEnd,
}: SelectedLocationMarkerProps) {
  function handleDragEnd(event: MarkerDragEvent) {
    onDragEnd({
      lng: event.lngLat.lng,
      lat: event.lngLat.lat,
    })
  }

  return (
    <Marker
      longitude={position.lng}
      latitude={position.lat}
      draggable={true}
      onDragEnd={handleDragEnd}
      anchor="bottom"
    >
      <img
        src="/map-pin.svg"
        alt="Selected location"
        className="h-9 w-9 select-none"
        draggable={false}
      />
    </Marker>
  )
}

export default SelectedLocationMarker
