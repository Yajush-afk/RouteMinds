import { LocateFixed, Minus, Plus } from "lucide-react"
import { motion, useReducedMotion } from "motion/react"

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
  const prefersReducedMotion = useReducedMotion()
  const sharedButtonClassName =
    "border border-slate-200 bg-white text-slate-700 shadow-none transition-[box-shadow,border-color,color,background-color] duration-250 ease-out hover:border-slate-300 hover:!bg-white hover:shadow-[0_4px_8px_2px_rgba(15,23,42,0.06)] focus-visible:border-slate-300 focus-visible:ring-0 focus-visible:shadow-[0_6px_10px_4px_rgba(15,23,42,0.08)]"

  return (
    <motion.div
      initial={prefersReducedMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: prefersReducedMotion ? 0 : 0.28 }}
      className="pointer-events-auto absolute right-5 bottom-16 z-850 flex flex-col items-center gap-2.5"
    >
      <motion.div
        initial={prefersReducedMotion ? false : { opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: prefersReducedMotion ? 0 : 0.45,
          delay: prefersReducedMotion ? 0 : 0.08,
          ease: [0.16, 1, 0.3, 1],
        }}
      >
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
      </motion.div>

      <motion.div
        initial={prefersReducedMotion ? false : { opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: prefersReducedMotion ? 0 : 0.45,
          delay: prefersReducedMotion ? 0 : 0.24,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="flex flex-col gap-1.5 rounded-[1.15rem]"
      >
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
      </motion.div>
    </motion.div>
  )
}

export default MapControls
