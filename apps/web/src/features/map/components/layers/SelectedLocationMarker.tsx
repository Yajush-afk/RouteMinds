import { memo } from "react"

import { Marker } from "react-map-gl/maplibre"
import type { MarkerDragEvent } from "react-map-gl/maplibre"

import type { LngLat } from "@/features/map/domain/types"
import { cn } from "@workspace/ui/lib/utils"

type SelectedLocationMarkerProps = {
  position: LngLat
  badge: string
  tone: "origin" | "destination"
  onDragEnd: (position: LngLat) => void
}

function SelectedLocationMarker({
  position,
  badge,
  tone,
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
      <div className="relative select-none">
        <span
          className={cn(
            "absolute -top-1 left-1/2 z-10 grid h-6 min-w-6 -translate-x-1/2 place-items-center rounded-full border-2 border-white px-1 text-[11px] font-semibold text-white shadow-md",
            tone === "origin" ? "bg-sky-500" : "bg-rose-500"
          )}
        >
          {badge}
        </span>
        <img
          src="/map-pin.svg"
          alt="Selected location"
          className="h-9 w-9 select-none"
          draggable={false}
        />
      </div>
    </Marker>
  )
}

export default memo(SelectedLocationMarker)
