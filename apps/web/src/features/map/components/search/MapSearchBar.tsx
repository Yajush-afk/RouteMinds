import { memo, useEffect, useMemo, useRef, useState } from "react"
import type { KeyboardEvent } from "react"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import {
  CircleAlert,
  Flag,
  LoaderCircle,
  MapPin,
  MapPinned,
} from "lucide-react"

import type { BackendHealthState } from "@/features/map/hooks/useBackendHealth"
import type { PlaceSuggestion } from "@/features/map/domain/types"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@workspace/ui/components/input-group"
import { cn } from "@workspace/ui/lib/utils"

type MapSearchBarProps = {
  backendHealth: BackendHealthState
  originText: string
  originResults: PlaceSuggestion[]
  isOriginSearching: boolean
  showNoOriginResults: boolean
  destinationText: string
  destinationResults: PlaceSuggestion[]
  isDestinationSearching: boolean
  showNoDestinationResults: boolean
  onOriginChange: (next: string) => void
  onOriginFocus: () => void
  onOriginBlur: () => void
  onOriginSelect: (result: PlaceSuggestion) => void
  onDestinationChange: (next: string) => void
  onDestinationFocus: () => void
  onDestinationSelect: (result: PlaceSuggestion) => void
}

function MapSearchBar({
  backendHealth,
  originText,
  originResults,
  isOriginSearching,
  showNoOriginResults,
  destinationText,
  destinationResults,
  isDestinationSearching,
  showNoDestinationResults,
  onOriginChange,
  onOriginFocus,
  onOriginBlur,
  onOriginSelect,
  onDestinationChange,
  onDestinationFocus,
  onDestinationSelect,
}: MapSearchBarProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const prefersReducedMotion = useReducedMotion()
  const [activeField, setActiveField] = useState<"from" | "to" | null>(null)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)

  const showOriginPanel =
    isOriginSearching || originResults.length > 0 || showNoOriginResults
  const isOriginOpen = activeField === "from" && showOriginPanel
  const showDestinationPanel =
    isDestinationSearching ||
    destinationResults.length > 0 ||
    showNoDestinationResults
  const isDestinationOpen = activeField === "to" && showDestinationPanel

  const activeResults = useMemo(() => {
    if (activeField === "from") {
      return originResults
    }

    if (activeField === "to") {
      return destinationResults
    }

    return []
  }, [activeField, destinationResults, originResults])

  const dropdownMotion = prefersReducedMotion
    ? { initial: false as const, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : {
        initial: { opacity: 0, y: -4 },
        animate: { opacity: 1, y: 0 },
        exit: { opacity: 0, y: -2 },
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

  const normalizedHighlightedIndex =
    activeResults.length > 0
      ? highlightedIndex < 0 || highlightedIndex >= activeResults.length
        ? 0
        : highlightedIndex
      : -1

  const selectableResult = useMemo(() => {
    if (
      normalizedHighlightedIndex < 0 ||
      normalizedHighlightedIndex >= activeResults.length
    ) {
      return null
    }
    return activeResults[normalizedHighlightedIndex]
  }, [activeResults, normalizedHighlightedIndex])

  const handleOriginKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      setActiveField(null)
      setHighlightedIndex(-1)
      return
    }

    if (!originResults.length) {
      return
    }

    if (event.key === "ArrowDown") {
      event.preventDefault()
      setActiveField("from")
      setHighlightedIndex(
        (normalizedHighlightedIndex + 1) % originResults.length
      )
      return
    }

    if (event.key === "ArrowUp") {
      event.preventDefault()
      setActiveField("from")
      setHighlightedIndex(
        (normalizedHighlightedIndex - 1 + originResults.length) %
          originResults.length
      )
      return
    }

    if (event.key === "Enter" && selectableResult) {
      event.preventDefault()
      onOriginSelect(selectableResult)
      setActiveField(null)
      setHighlightedIndex(-1)
    }
  }

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
      setHighlightedIndex(
        (normalizedHighlightedIndex + 1) % destinationResults.length
      )
      return
    }

    if (event.key === "ArrowUp") {
      event.preventDefault()
      setActiveField("to")
      setHighlightedIndex(
        (normalizedHighlightedIndex - 1 + destinationResults.length) %
          destinationResults.length
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

  function renderResultsPanel(
    results: PlaceSuggestion[],
    isSearching: boolean,
    showNoResults: boolean,
    onSelect: (result: PlaceSuggestion) => void,
    emptyMessage: string
  ) {
    return (
      <motion.div
        initial={dropdownMotion.initial}
        animate={dropdownMotion.animate}
        exit={dropdownMotion.exit}
        transition={{
          duration: prefersReducedMotion ? 0 : 0.16,
          ease: "easeOut",
        }}
        className="absolute top-full z-20 mt-2 w-full overflow-hidden rounded-[1.2rem] border border-white/55 bg-white/46 p-1.5 shadow-[0_18px_48px_rgba(15,23,42,0.16)] backdrop-blur-2xl supports-backdrop-filter:bg-white/38"
      >
        <div className="pointer-events-none absolute inset-0 rounded-[inherit] bg-linear-to-br from-white/34 via-white/10 to-transparent" />
        <div className="pointer-events-none absolute inset-x-4 top-0 h-px bg-linear-to-r from-transparent via-white/90 to-transparent" />

        {isSearching ? (
          <div className="flex items-center gap-2 rounded-[0.95rem] border border-white/60 bg-white/58 px-3 py-2.5 text-sm text-slate-600">
            <LoaderCircle className="size-4 animate-spin text-slate-500" />
            <p>Searching locations...</p>
          </div>
        ) : null}

        {!isSearching ? (
          <ul className="max-h-52 overflow-y-auto rounded-[0.95rem] border border-slate-200/70 bg-white">
            {results.map((result, index) => (
              <li
                key={result.id}
                className={cn(
                  index > 0 ? "border-t border-slate-200/80" : undefined
                )}
              >
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => {
                    onSelect(result)
                    setActiveField(null)
                    setHighlightedIndex(-1)
                  }}
                  className={cn(
                    "w-full px-3 py-2.5 text-left text-sm transition-colors duration-150",
                    normalizedHighlightedIndex === index
                      ? "bg-slate-100 text-slate-800"
                      : "text-slate-700"
                  )}
                >
                  <span className="flex items-start gap-3">
                    <span
                      className={cn(
                        "mt-0.5 grid size-7 shrink-0 place-items-center rounded-[0.8rem] border",
                        normalizedHighlightedIndex === index
                          ? "border-white/80 bg-white/78 text-slate-700"
                          : "border-white/55 bg-white/46 text-slate-500"
                      )}
                    >
                      <MapPin className="size-3.5" />
                    </span>
                    <span className="min-w-0 leading-snug">{result.label}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}

        {!isSearching && showNoResults && results.length === 0 && (
          <div className="flex items-center gap-2 rounded-[0.95rem] border border-white/60 bg-white/56 px-3 py-2.5 text-sm text-slate-600">
            <CircleAlert className="size-4 text-slate-500" />
            <p>{emptyMessage}</p>
          </div>
        )}
      </motion.div>
    )
  }

  function getFieldClassName() {
    return cn(
      "min-h-12 rounded-[1rem] border border-slate-200 bg-white px-1.5 shadow-none transition-[box-shadow,border-color] duration-250 ease-out hover:border-slate-300 hover:bg-white has-[[data-slot=input-group-control]:focus-visible]:shadow-[0_6px_10px_4px_rgba(15,23,42,0.08)] has-[[data-slot=input-group-control]:focus-visible]:ring-0 dark:!border-slate-200 dark:!bg-white dark:hover:!border-slate-300"
    )
  }

  function getIconBadgeClassName() {
    return "grid size-7 place-items-center text-slate-500 transition-colors duration-200"
  }

  function getBackendIndicatorClassName() {
    if (backendHealth.status === "online") {
      return "bg-emerald-500"
    }

    if (backendHealth.status === "offline") {
      return "bg-rose-500"
    }

    return "bg-amber-500"
  }

  function getBackendStatusLabel() {
    if (backendHealth.status === "online") {
      return "API online"
    }

    if (backendHealth.status === "offline") {
      return "API offline"
    }

    return "Checking API"
  }

  return (
    <motion.div
      ref={containerRef}
      initial={prefersReducedMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: prefersReducedMotion ? 0 : 0.28 }}
      className="pointer-events-auto absolute top-4 left-1/2 z-850 w-[min(calc(100%-2rem),32rem)] -translate-x-1/2"
    >
      <motion.div
        initial={prefersReducedMotion ? false : { opacity: 0, y: -28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: prefersReducedMotion ? 0 : 0.45,
          delay: prefersReducedMotion ? 0 : 0.08,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="relative"
      >
        <div className="mb-2 rounded-[1.15rem] border border-white/55 bg-white/50 px-3 py-2 shadow-[0_12px_30px_rgba(15,23,42,0.12)] backdrop-blur-xl supports-backdrop-filter:bg-white/40">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2">
              {backendHealth.status === "checking" ? (
                <LoaderCircle className="size-3.5 shrink-0 animate-spin text-amber-600" />
              ) : (
                <span
                  className={cn(
                    "size-2 shrink-0 rounded-full shadow-[0_0_0_3px_rgba(255,255,255,0.72)]",
                    getBackendIndicatorClassName()
                  )}
                />
              )}
              <p className="truncate text-[12px] font-semibold tracking-[0.02em] text-slate-700">
                {getBackendStatusLabel()}
              </p>
            </div>

            <p className="max-w-[13rem] truncate text-[11px] text-slate-500">
              {backendHealth.apiBaseUrl}
            </p>
          </div>

          <p className="mt-1 text-[11px] leading-relaxed text-slate-600">
            {backendHealth.description}
          </p>
        </div>

        <InputGroup className={cn("w-full", getFieldClassName())}>
          <InputGroupInput
            placeholder="From"
            value={originText}
            onFocus={(event) => {
              setActiveField("from")
              setHighlightedIndex(originResults.length > 0 ? 0 : -1)
              onOriginFocus()

              if (
                event.currentTarget.value.trim() &&
                event.currentTarget.value !== "Your Location"
              ) {
                event.currentTarget.select()
              }
            }}
            onChange={(event) => onOriginChange(event.target.value)}
            onBlur={onOriginBlur}
            onKeyDown={handleOriginKeyDown}
            className="h-12 px-3 text-[15px] font-medium text-slate-800 placeholder:text-slate-500"
          />
          <InputGroupAddon
            align="inline-start"
            className="pr-0 pl-2.5 text-slate-500"
          >
            <span className={getIconBadgeClassName()}>
              <MapPinned className="size-3.5" />
            </span>
          </InputGroupAddon>
        </InputGroup>

        <AnimatePresence initial={false}>
          {isOriginOpen
            ? renderResultsPanel(
                originResults,
                isOriginSearching,
                showNoOriginResults,
                onOriginSelect,
                "No origins found in Delhi."
              )
            : null}
        </AnimatePresence>
      </motion.div>

      <motion.div
        initial={prefersReducedMotion ? false : { opacity: 0, y: -28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          duration: prefersReducedMotion ? 0 : 0.45,
          delay: prefersReducedMotion ? 0 : 0.24,
          ease: [0.16, 1, 0.3, 1],
        }}
        className="relative mt-2"
      >
        <InputGroup className={cn("w-full", getFieldClassName())}>
          <InputGroupInput
            placeholder="To"
            value={destinationText}
            autoComplete="off"
            onFocus={(event) => {
              setActiveField("to")
              setHighlightedIndex(destinationResults.length > 0 ? 0 : -1)
              onDestinationFocus()

              if (event.currentTarget.value.trim()) {
                event.currentTarget.select()
              }
            }}
            onChange={(event) => {
              onDestinationChange(event.target.value)
              setActiveField("to")
            }}
            onKeyDown={handleDestinationKeyDown}
            className="h-12 px-3 text-[15px] font-medium text-slate-800 placeholder:text-slate-500"
          />
          <InputGroupAddon
            align="inline-start"
            className="pr-0 pl-2.5 text-slate-500"
          >
            <span className={getIconBadgeClassName()}>
              <Flag className="size-3.5" />
            </span>
          </InputGroupAddon>
        </InputGroup>

        <AnimatePresence initial={false}>
          {isDestinationOpen
            ? renderResultsPanel(
                destinationResults,
                isDestinationSearching,
                showNoDestinationResults,
                onDestinationSelect,
                "No destinations found in Delhi."
              )
            : null}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  )
}

export default memo(MapSearchBar)
