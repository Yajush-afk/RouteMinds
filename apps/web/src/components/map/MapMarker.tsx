import { Marker } from "react-leaflet"
import { Icon } from "leaflet"
import type { LatLngTuple, Marker as LeafletMarker } from "leaflet"

type MapMarkerProps = {
  position: LatLngTuple
  isAllowedPosition: (nextPosition: LatLngTuple) => boolean
  onPositionChange: (nextPosition: LatLngTuple) => void
}

const routeMindsPinIcon = new Icon({
  iconUrl: "/map-pin.svg",
  iconSize: [36, 36],
  iconAnchor: [18, 36],
  popupAnchor: [0, -32],
})

function MapMarker({
  position,
  isAllowedPosition,
  onPositionChange,
}: MapMarkerProps) {
  return (
    <Marker
      position={position}
      icon={routeMindsPinIcon}
      draggable={true}
      eventHandlers={{
        dragend: (event) => {
          const marker = event.target as LeafletMarker
          const { lat, lng } = marker.getLatLng()
          const nextPosition: LatLngTuple = [lat, lng]

          if (isAllowedPosition(nextPosition)) {
            onPositionChange(nextPosition)
            return
          }

          // Keep marker constrained to the last valid Delhi coordinate.
          marker.setLatLng(position)
        },
      }}
    />
  )
}

export default MapMarker
