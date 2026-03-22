import { useEffect, useMemo, useRef, useState } from "react"
import type { KeyboardEvent } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { Locate, Search } from "lucide-react"

import type { PlaceSuggestion } from "@/features/map/domain/types"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@workspace/ui/components/input-group"
import { cn } from "@workspace/ui/lib/utils"

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
  const containerRef = useRef<HTMLDivElement>(null)
  const prefersReducedMotion = useReducedMotion()
  const [activeField, setActiveField] = useState<"from" | "to" | null>(null)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)

  const showDestinationPanel =
    isDestinationSearching ||
    destinationResults.length > 0 ||
    showNoDestinationResults
  const isDestinationOpen = activeField === "to" && showDestinationPanel

  const dropdownMotion = prefersReducedMotion
    ? { initial: false as const, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, y: -6, scale: 0.98 },
        animate: { opacity: 1, y: 0, scale: 1 },
        exit: { opacity: 0, y: -4, scale: 0.98 },
      }

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setActiveField(null)
        setHighlightedIndex(-1)
      }
    }

    document.addEventListener("mousedown", handleOutsideClick)
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick)
    }
  }, [])

  useEffect(() => {
    if (activeField !== "to") {
      return
    }

    if (destinationResults.length === 0) {
      setHighlightedIndex(-1)
      return
    }

    if (highlightedIndex < 0 || highlightedIndex >= destinationResults.length) {
      setHighlightedIndex(0)
    }
  }, [activeField, destinationResults, highlightedIndex])

  const selectableResult = useMemo(() => {
    if (highlightedIndex < 0 || highlightedIndex >= destinationResults.length) {
      return null
    }
    return destinationResults[highlightedIndex]
  }, [destinationResults, highlightedIndex])

  const handleDestinationKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setActiveField(null)
      setHighlightedIndex(-1)
      return
    }

    if (!destinationResults.length) {
      return
    }

    if (event.key === "ArrowDown") {
      event.preventDefault()
      setActiveField("to")
      setHighlightedIndex((prev) => (prev + 1) % destinationResults.length)
      return
    }

    if (event.key === "ArrowUp") {
      event.preventDefault()
      setActiveField("to")
      setHighlightedIndex(
        (prev) =>
          (prev - 1 + destinationResults.length) % destinationResults.length
      )
      return
    }

    if (event.key === "Enter" && selectableResult) {
      event.preventDefault()
      onDestinationSelect(selectableResult)
      setActiveField(null)
      setHighlightedIndex(-1)
    }
  }

  return (
    <div className="pointer-events-auto absolute top-4 left-1/2 z-850 w-[min(calc(100%-2rem),30rem)] -translate-x-1/2">
      <motion.div
        ref={containerRef}
        initial={
          prefersReducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }
        }
        animate={{ opacity: 1, scale: 1 }}
        transition={{
          duration: prefersReducedMotion ? 0.12 : 0.24,
          ease: [0, 0.71, 0.2, 1.01],
        }}
        className="flex flex-col gap-2 rounded-xl border border-border/70 bg-card/95 p-2 shadow-[0_14px_40px_rgba(15,23,42,0.2)] backdrop-blur supports-backdrop-filter:bg-card/82"
      >
        <InputGroup className="w-full bg-background/70">
          <InputGroupInput
            placeholder="From..."
            value={originText}
            onFocus={() => setActiveField("from")}
            onChange={(event) => onOriginChange(event.target.value)}
          />
          <InputGroupAddon align="inline-start">
            <Search />
          </InputGroupAddon>
        </InputGroup>

        <div className="relative">
          <InputGroup className="w-full bg-background/70">
            <InputGroupInput
              placeholder="To..."
              value={destinationText}
              autoComplete="off"
              onFocus={() => {
                setActiveField("to")
                setHighlightedIndex(destinationResults.length > 0 ? 0 : -1)
              }}
              onChange={(event) => {
                onDestinationChange(event.target.value)
                setActiveField("to")
              }}
              onKeyDown={handleDestinationKeyDown}
            />
            <InputGroupAddon align="inline-start">
              <Locate />
            </InputGroupAddon>
          </InputGroup>

          <AnimatePresence initial={false}>
            {isDestinationOpen ? (
              <motion.div
                initial={dropdownMotion.initial}
                animate={dropdownMotion.animate}
                exit={dropdownMotion.exit}
                transition={{
                  duration: prefersReducedMotion ? 0 : 0.16,
                  ease: "easeOut",
                }}
                className="absolute top-full z-20 mt-1 w-full overflow-hidden rounded-lg border border-border bg-card p-1 shadow-md"
              >
                {isDestinationSearching ? (
                  <p className="px-2.5 py-2 text-sm text-muted-foreground">
                    Searching destinations...
                  </p>
                ) : null}

                {!isDestinationSearching ? (
                  <ul className="max-h-52 overflow-y-auto">
                    {destinationResults.map((result, index) => (
                      <motion.li
                        key={result.id}
                        initial={
                          prefersReducedMotion ? false : { opacity: 0, y: -3 }
                        }
                        animate={{ opacity: 1, y: 0 }}
                        transition={{
                          duration: prefersReducedMotion ? 0 : 0.12,
                          delay: prefersReducedMotion ? 0 : index * 0.015,
                        }}
                      >
                        <button
                          type="button"
                          onMouseDown={(event) => event.preventDefault()}
                          onMouseEnter={() => setHighlightedIndex(index)}
                          onClick={() => {
                            onDestinationSelect(result)
                            setActiveField(null)
                            setHighlightedIndex(-1)
                          }}
                          className={cn(
                            "w-full rounded-md px-2.5 py-1.5 text-left text-sm transition-colors",
                            highlightedIndex === index
                              ? "bg-muted text-foreground"
                              : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                          )}
                        >
                          {result.label}
                        </button>
                      </motion.li>
                    ))}
                  </ul>
                ) : null}

                {!isDestinationSearching &&
                  showNoDestinationResults &&
                  destinationResults.length === 0 && (
                    <p className="px-2.5 py-2 text-sm text-muted-foreground">
                      No destinations found in Delhi.
                    </p>
                  )}
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  )
}

export default MapSearchBar
