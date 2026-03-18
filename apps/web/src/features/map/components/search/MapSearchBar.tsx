import { AnimatePresence, motion, useReducedMotion } from "motion/react"

import type { PlaceSuggestion } from "@/features/map/domain/types"
import { Input } from "@workspace/ui/components/input"

type MapSearchBarProps = {
  originText: string
  destinationText: string
  destinationResults: PlaceSuggestion[]
  isDestinationSearching: boolean
  showNoDestinationResults: boolean
  onOriginChange: (next: string) => void
  onDestinationChange: (next: string) => void
  onDestinationSelect: (result: PlaceSuggestion) => void
}

function MapSearchBar({
  originText,
  destinationText,
  destinationResults,
  isDestinationSearching,
  showNoDestinationResults,
  onOriginChange,
  onDestinationChange,
  onDestinationSelect,
}: MapSearchBarProps) {
  const prefersReducedMotion = useReducedMotion()
  const showDestinationResults =
    isDestinationSearching ||
    destinationResults.length > 0 ||
    showNoDestinationResults
  const transition = {
    duration: prefersReducedMotion ? 0.12 : 0.18,
    ease: [0.23, 1, 0.32, 1] as const,
  }

  return (
    <div className="pointer-events-auto absolute top-4 left-1/2 z-850 w-[min(calc(100%-2rem),48rem)] -translate-x-1/2">
      <motion.div
        layout
        initial={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={transition}
        className="overflow-hidden rounded-[1.4rem] border border-border/70 bg-card/95 shadow-[0_18px_60px_rgba(15,23,42,0.16)] backdrop-blur supports-backdrop-filter:bg-card/82"
      >
        <div className="grid gap-3 p-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)] md:p-3.5">
          <label className="grid gap-1.5 rounded-[1rem] bg-background/55 p-2.5">
            <span className="px-1 text-[11px] font-medium tracking-[0.14em] text-muted-foreground uppercase">
              From
            </span>
            <Input
              type="text"
              value={originText}
              placeholder="Your location"
              className="border-transparent bg-transparent shadow-none"
              onChange={(event) => onOriginChange(event.target.value)}
            />
          </label>

          <label className="grid gap-1.5 rounded-[1rem] bg-background/55 p-2.5">
            <span className="px-1 text-[11px] font-medium tracking-[0.14em] text-muted-foreground uppercase">
              To
            </span>
            <Input
              type="text"
              value={destinationText}
              placeholder="Choose destination"
              autoComplete="off"
              className="border-transparent bg-transparent shadow-none"
              onChange={(event) => onDestinationChange(event.target.value)}
            />
          </label>
        </div>

        <AnimatePresence initial={false}>
          {showDestinationResults && (
            <motion.div
              layout
              initial={
                prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -6 }
              }
              animate={{ opacity: 1, y: 0 }}
              exit={
                prefersReducedMotion ? { opacity: 0 } : { opacity: 0, y: -4 }
              }
              transition={transition}
              className="border-t border-border/60 bg-background/70 px-3 pt-2 pb-3"
            >
              <div className="overflow-hidden rounded-[1rem] bg-background/90 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
                {isDestinationSearching && (
                  <p className="px-4 py-3 text-sm text-muted-foreground">
                    Searching destinations...
                  </p>
                )}

                {!isDestinationSearching &&
                  destinationResults.map((result, index) => (
                    <motion.button
                      key={result.id}
                      type="button"
                      initial={
                        prefersReducedMotion ? false : { opacity: 0, y: -4 }
                      }
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: prefersReducedMotion ? 0.1 : 0.14,
                        delay: prefersReducedMotion ? 0 : index * 0.025,
                        ease: [0.23, 1, 0.32, 1],
                      }}
                      className="block w-full border-b border-border/60 px-4 py-3 text-left text-sm transition-colors last:border-b-0 hover:bg-accent"
                      onClick={() => onDestinationSelect(result)}
                    >
                      {result.label}
                    </motion.button>
                  ))}

                {!isDestinationSearching &&
                  showNoDestinationResults &&
                  destinationResults.length === 0 && (
                    <p className="px-4 py-3 text-sm text-muted-foreground">
                      No destinations found in Delhi.
                    </p>
                  )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

export default MapSearchBar
