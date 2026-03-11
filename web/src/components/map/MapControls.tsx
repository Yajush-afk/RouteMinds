import type { LatLngTuple } from "leaflet"
import { LocateFixed, Minus, Plus } from "lucide-react"
import { useMap } from "react-leaflet"

import { Button } from "@/components/ui/button"
import { getBrowserLocation } from "@/lib/geolocation"

type MapControlsProps = {
  isLocating: boolean
  onLocateStart: () => void
  onLocateSuccess: (nextPosition: LatLngTuple) => void
  onLocateError: (message: string) => void
}

function MapControls({
  isLocating,
  onLocateStart,
  onLocateSuccess,
  onLocateError,
}: MapControlsProps) {
  const map = useMap()

  const handleLocate = async () => {
    onLocateStart()

    try {
      const nextPosition = await getBrowserLocation()
      onLocateSuccess(nextPosition)
      map.setView(nextPosition, 30, { animate: true })
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to retrieve your location."

      onLocateError(message)
    }
  }

  return (
    <div className="pointer-events-auto absolute right-5 bottom-5 z-[1000] flex flex-col items-center gap-2 rounded-xl">
      <Button
        type="button"
        size="icon"
        onClick={handleLocate}
        disabled={isLocating}
        aria-label="Locate me"
        title="Locate me"
      >
        <LocateFixed className={isLocating ? "animate-pulse" : undefined} />
      </Button>
      <div className="flex flex-col gap-1 rounded-md border border-border bg-card p-1">
        <Button
          type="button"
          size="icon"
          onClick={() => map.zoomIn()}
          aria-label="Zoom in"
          title="Zoom in"
        >
          <Plus />
        </Button>
        <Button
          type="button"
          size="icon"
          onClick={() => map.zoomOut()}
          aria-label="Zoom out"
          title="Zoom out"
        >
          <Minus />
        </Button>
      </div>
    </div>
  )
}

export default MapControls
