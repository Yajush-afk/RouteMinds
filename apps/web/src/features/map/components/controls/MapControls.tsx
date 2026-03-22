import { LocateFixed, Minus, Plus } from "lucide-react"

import { Button } from "@workspace/ui/components/button"

type MapControlsProps = {
  isLocating: boolean
  onLocateRequest: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}

function MapControls({
  isLocating,
  onLocateRequest,
  onZoomIn,
  onZoomOut,
}: MapControlsProps) {
  return (
    <div className="pointer-events-auto absolute right-5 bottom-5 z-850 flex flex-col items-center gap-2">
      <Button
        type="button"
        size="icon"
        onClick={onLocateRequest}
        disabled={isLocating}
        aria-label="Locate me"
        title="Locate me"
      >
        <LocateFixed className={isLocating ? "animate-pulse" : undefined} />
      </Button>

      <div className="flex flex-col gap-1 rounded-xl border border-border bg-card/95 p-1 shadow-lg backdrop-blur supports-backdrop-filter:bg-card/80">
        <Button
          type="button"
          size="icon"
          variant="ghost"
          onClick={onZoomIn}
          aria-label="Zoom in"
          title="Zoom in"
        >
          <Plus />
        </Button>

        <Button
          type="button"
          size="icon"
          variant="ghost"
          onClick={onZoomOut}
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
