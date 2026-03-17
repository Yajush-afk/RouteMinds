import { useMapEvents } from "react-leaflet"
import type { LatLngTuple } from "leaflet"

type MapClickHandlerProps = {
  onSingleClickPan: (nextCenter: LatLngTuple) => void
  onContextMenuPlace: (nextPosition: LatLngTuple) => void
}

function MapClickHandler({
  onSingleClickPan,
  onContextMenuPlace,
}: MapClickHandlerProps) {
  const map = useMapEvents({
    click: (event) => {
      const nextCenter: LatLngTuple = [event.latlng.lat, event.latlng.lng]
      onSingleClickPan(nextCenter)
      map.setView(event.latlng, map.getZoom(), { animate: true })
    },
    contextmenu: (event) => {
      event.originalEvent.preventDefault()
      const nextPosition: LatLngTuple = [event.latlng.lat, event.latlng.lng]
      onContextMenuPlace(nextPosition)
    },
  })

  return null
}

export default MapClickHandler
