import { memo } from "react"
import { CircleDot } from "lucide-react"

import { Marker } from "react-map-gl/maplibre"

import type { LngLat } from "@/features/map/domain/types"
import { cn } from "@workspace/ui/lib/utils"

type SelectedLocationMarkerProps = {
  position: LngLat
  badge: string
  tone: "origin" | "destination"
  variant?: "default" | "user-location"
}

function SelectedLocationMarker({
  position,
  badge,
  tone,
  variant = "default",
}: SelectedLocationMarkerProps) {
  if (variant === "user-location") {
    return (
      <Marker longitude={position.lng} latitude={position.lat} anchor="center">
        <div className="relative grid size-8 select-none place-items-center">
          <span className="absolute size-8 rounded-full bg-sky-500/20 animate-ping" />
          <span className="absolute size-8 rounded-full border border-sky-300/80 bg-sky-400/15 shadow-[0_0_0_1px_rgba(255,255,255,0.45)]" />
          <span className="absolute size-5 rounded-full bg-white/95 shadow-[0_0_0_4px_rgba(14,165,233,0.2)]" />
          <CircleDot
            aria-label="Your location"
            className="relative z-10 size-5 text-sky-600 drop-shadow-[0_1px_2px_rgba(15,23,42,0.18)]"
            strokeWidth={2.25}
          />
        </div>
      </Marker>
    )
  }

  return (
    <Marker longitude={position.lng} latitude={position.lat} anchor="bottom">
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
