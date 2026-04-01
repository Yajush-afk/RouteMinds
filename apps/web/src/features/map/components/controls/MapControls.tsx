import { memo } from "react"

import { LocateFixed, Minus, Plus } from "lucide-react"

import { Button } from "@workspace/ui/components/button"
import { cn } from "@workspace/ui/lib/utils"

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
  const sharedButtonClassName =
    "border border-slate-200 bg-white text-slate-700 shadow-none transition-[box-shadow,border-color,color,background-color] duration-250 ease-out hover:border-slate-300 hover:!bg-white hover:shadow-[0_4px_8px_2px_rgba(15,23,42,0.06)] focus-visible:border-slate-300 focus-visible:ring-0 focus-visible:shadow-[0_6px_10px_4px_rgba(15,23,42,0.08)]"

  return (
    <div className="pointer-events-auto absolute right-5 bottom-16 z-850 flex flex-col items-center gap-2.5">
      <div className="transition-opacity duration-200 ease-out motion-reduce:transition-none">
        <Button
          type="button"
          size="icon-lg"
          onClick={onLocateRequest}
          disabled={isLocating}
          aria-label="Locate me"
          title="Locate me"
          className={cn(
            "rounded-[1rem]",
            sharedButtonClassName,
            "disabled:border-slate-200 disabled:bg-white disabled:text-slate-400"
          )}
        >
          <LocateFixed
            className={cn(
              "size-4.5",
              isLocating ? "animate-pulse text-slate-500" : undefined
            )}
          />
        </Button>
      </div>

      <div className="flex flex-col gap-1.5 rounded-[1.15rem] transition-opacity duration-200 ease-out motion-reduce:transition-none">
        <Button
          type="button"
          size="icon"
          onClick={onZoomIn}
          aria-label="Zoom in"
          title="Zoom in"
          className={cn("rounded-[0.9rem]", sharedButtonClassName)}
        >
          <Plus className="size-4" />
        </Button>

        <Button
          type="button"
          size="icon"
          onClick={onZoomOut}
          aria-label="Zoom out"
          title="Zoom out"
          className={cn("rounded-[0.9rem]", sharedButtonClassName)}
        >
          <Minus className="size-4" />
        </Button>
      </div>
    </div>
  )
}

export default memo(MapControls)
