import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import {
  memo,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react"
import type { KeyboardEvent } from "react"
import { createPortal } from "react-dom"
import {
  Check,
  GripVertical,
  LoaderCircle,
  MapPin,
  Search,
  Trash2,
  X,
} from "lucide-react"

import type { StopSearchResult } from "@/features/map/domain/types"
import { useStopSearch } from "@/features/map/hooks/useStopSearch"
import { Button } from "@workspace/ui/components/button"
import { Input } from "@workspace/ui/components/input"
import { cn } from "@workspace/ui/lib/utils"

type MapRouteWaypointFieldProps = {
  waypointId: string
  badge: string
  query: string
  selectedStop: StopSearchResult | null
  canRemove: boolean
  isFirst: boolean
  isLast: boolean
  onQueryChange: (nextQuery: string) => void
  onSelect: (stop: StopSearchResult) => void
  onClear: () => void
  onRemove: () => void
}

type DropdownPosition = {
  top?: number
  bottom?: number
  left: number
  width: number
  maxHeight: number
}

function MapRouteWaypointField({
  waypointId,
  badge,
  query,
  selectedStop,
  canRemove,
  isFirst,
  isLast,
  onQueryChange,
  onSelect,
  onClear,
  onRemove,
}: MapRouteWaypointFieldProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputId = `waypoint-input-${waypointId}`
  const listboxId = useId()
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const [dropdownPosition, setDropdownPosition] =
    useState<DropdownPosition | null>(null)
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
    isOver,
  } = useSortable({ id: waypointId })

  const shouldSearch =
    query.trim().length >= 2 &&
    (!selectedStop || selectedStop.stopName !== query.trim())

  const { results, isSearching, hasAttempted, errorMessage } = useStopSearch(
    query,
    shouldSearch
  )

  const showNoResults =
    shouldSearch &&
    hasAttempted &&
    !isSearching &&
    !errorMessage &&
    results.length === 0

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      const target = event.target as Node

      if (
        !containerRef.current?.contains(target) &&
        !dropdownRef.current?.contains(target)
      ) {
        setIsOpen(false)
        setHighlightedIndex(-1)
      }
    }

    document.addEventListener("mousedown", handleOutsideClick)
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick)
    }
  }, [])

  const effectiveHighlightedIndex =
    results.length === 0
      ? -1
      : highlightedIndex >= results.length
        ? -1
        : highlightedIndex

  function handleSelect(stop: StopSearchResult) {
    onSelect(stop)
    setIsOpen(false)
    setHighlightedIndex(-1)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setIsOpen(false)
      setHighlightedIndex(-1)
      return
    }

    if (!results.length) {
      return
    }

    if (event.key === "ArrowDown") {
      event.preventDefault()
      setIsOpen(true)
      setHighlightedIndex((currentIndex) =>
        currentIndex < 0 ? 0 : (currentIndex + 1) % results.length
      )
      return
    }

    if (event.key === "ArrowUp") {
      event.preventDefault()
      setIsOpen(true)
      setHighlightedIndex((currentIndex) =>
        currentIndex < 0
          ? results.length - 1
          : (currentIndex - 1 + results.length) % results.length
      )
      return
    }

    if (
      event.key === "Enter" &&
      effectiveHighlightedIndex >= 0 &&
      effectiveHighlightedIndex < results.length
    ) {
      event.preventDefault()
      handleSelect(results[effectiveHighlightedIndex])
    }
  }

  const showDropdown =
    isOpen &&
    (isSearching || results.length > 0 || showNoResults || !!errorMessage)

  useLayoutEffect(() => {
    if (!showDropdown) {
      return
    }

    function updateDropdownPosition() {
      const container = containerRef.current
      if (!container) {
        return
      }

      const rect = container.getBoundingClientRect()
      const viewportGap = 16
      const fieldGap = 8
      const preferredHeight = 430
      const availableBelow = window.innerHeight - rect.bottom - viewportGap
      const availableAbove = rect.top - viewportGap
      const shouldOpenAbove =
        availableBelow < preferredHeight && availableAbove > availableBelow
      const availableHeight = shouldOpenAbove
        ? availableAbove - fieldGap
        : availableBelow - fieldGap

      setDropdownPosition({
        top: shouldOpenAbove ? undefined : rect.bottom + fieldGap,
        bottom: shouldOpenAbove
          ? window.innerHeight - rect.top + fieldGap
          : undefined,
        left: rect.left,
        width: rect.width - (canRemove ? 40 : 0),
        maxHeight: Math.max(180, availableHeight),
      })
    }

    updateDropdownPosition()
    window.addEventListener("resize", updateDropdownPosition)
    window.addEventListener("scroll", updateDropdownPosition, true)

    return () => {
      window.removeEventListener("resize", updateDropdownPosition)
      window.removeEventListener("scroll", updateDropdownPosition, true)
    }
  }, [canRemove, showDropdown])

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  return (
    <div
      ref={(node) => {
        containerRef.current = node
        setNodeRef(node)
      }}
      style={style}
      className={cn(
        "relative z-0 transition-opacity",
        canRemove && "pr-10",
        showDropdown ? "z-50" : undefined,
        isDragging ? "z-[70] opacity-85" : undefined
      )}
    >
      {!isFirst ? (
        <span className="absolute -top-3.5 left-[1.65rem] h-3.5 w-px bg-slate-300" />
      ) : null}
      {!isLast ? (
        <span className="absolute -bottom-3.5 left-[1.65rem] h-3.5 w-px bg-slate-300" />
      ) : null}

      <div
        className={cn(
          "flex items-center gap-2.5 rounded-2xl border bg-white p-3 shadow-[0_10px_30px_-24px_rgba(15,23,42,0.5)] transition-[border-color,box-shadow,background-color]",
          selectedStop ? "border-slate-200" : "border-slate-200/80",
          isOver ? "border-sky-400 bg-sky-50/70 shadow-md" : undefined,
          isDragging ? "shadow-xl ring-2 ring-sky-300/60" : undefined
        )}
      >
        <div
          className={cn(
            "grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold ring-4 ring-white",
            selectedStop
              ? "bg-sky-600 text-white"
              : "border border-slate-300 bg-white text-slate-600"
          )}
          aria-hidden="true"
        >
          {badge}
        </div>

        <div className="min-w-0 flex-1">
          <div className="group/input relative">
            {selectedStop ? (
              <Check className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-emerald-600" />
            ) : (
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400 transition-opacity duration-200 ease-out group-focus-within/input:opacity-0" />
            )}
            <Input
              id={inputId}
              value={query}
              placeholder="Search for a bus stop"
              autoComplete="off"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded={showDropdown}
              aria-controls={showDropdown ? listboxId : undefined}
              onFocus={() => setIsOpen(true)}
              onChange={(event) => {
                onQueryChange(event.target.value)
                setIsOpen(true)
              }}
              onKeyDown={handleKeyDown}
              className={cn(
                "h-10 rounded-xl border-0 bg-slate-50 pr-9 pl-9 shadow-none transition-[padding] duration-200 ease-out placeholder:transition-opacity placeholder:duration-200 placeholder:ease-out focus:placeholder:opacity-0 focus-visible:border-0 focus-visible:ring-0",
                selectedStop ? "font-medium text-slate-900" : "focus:pl-3"
              )}
            />
            {query ? (
              <button
                type="button"
                onClick={onClear}
                className="absolute top-1/2 right-2 grid size-7 -translate-y-1/2 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-white hover:text-slate-700"
                aria-label={`Clear stop ${badge}`}
              >
                <X className="size-3.5" />
              </button>
            ) : null}
          </div>
        </div>

        <div className="flex shrink-0 items-center">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={`Reorder waypoint ${badge}`}
            className="cursor-grab touch-none rounded-lg text-slate-400 select-none hover:bg-slate-100 hover:text-slate-700 active:cursor-grabbing"
            {...attributes}
            {...listeners}
          >
            <GripVertical className="size-4" />
          </Button>
        </div>
      </div>

      {canRemove ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          onClick={onRemove}
          aria-label={`Remove stop ${badge}`}
          className="absolute top-1/2 right-0 size-8 -translate-y-1/2 rounded-full border border-slate-200/90 bg-white text-slate-400 shadow-[0_6px_18px_-10px_rgba(15,23,42,0.6)] transition-[color,background-color,border-color,box-shadow,transform] hover:-translate-y-[55%] hover:border-slate-300 hover:bg-slate-100 hover:text-slate-700 hover:shadow-[0_8px_20px_-10px_rgba(15,23,42,0.35)] focus-visible:border-slate-300 focus-visible:ring-2 focus-visible:ring-slate-200"
        >
          <Trash2 className="size-3.5 stroke-[1.8]" />
        </Button>
      ) : null}

      {showDropdown && dropdownPosition
        ? createPortal(
            <div
              ref={dropdownRef}
              style={dropdownPosition}
              className="fixed z-[1000] flex flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-[0_22px_60px_-24px_rgba(15,23,42,0.5)]"
            >
              {isSearching ? (
                <div className="space-y-3 px-4 py-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    <LoaderCircle className="size-4 animate-spin text-sky-600" />
                    Finding nearby stops
                  </div>
                  <div className="space-y-2" aria-hidden="true">
                    <div className="h-2.5 w-3/4 animate-pulse rounded-full bg-slate-100" />
                    <div className="h-2.5 w-1/2 animate-pulse rounded-full bg-slate-100" />
                  </div>
                </div>
              ) : null}

              {!isSearching && errorMessage ? (
                <div className="px-4 py-4">
                  <p className="text-sm font-medium text-rose-700">
                    We couldn&apos;t find stops right now
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">
                    {errorMessage}
                  </p>
                </div>
              ) : null}

              {!isSearching && !errorMessage && results.length > 0 ? (
                <>
                  <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
                    <p className="text-[11px] font-semibold tracking-[0.14em] text-slate-500 uppercase">
                      Suggested stops
                    </p>
                    <span className="text-xs text-slate-400">
                      {results.length} results
                    </span>
                  </div>
                  <ul
                    id={listboxId}
                    role="listbox"
                    className="subtle-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-contain p-2"
                  >
                    {results.map((result, index) => (
                      <li
                        key={`${result.stopId}-${result.stopName}`}
                        role="option"
                        aria-selected={index === effectiveHighlightedIndex}
                      >
                        <button
                          type="button"
                          onMouseDown={(event) => event.preventDefault()}
                          onMouseEnter={() => setHighlightedIndex(index)}
                          onClick={() => handleSelect(result)}
                          className={cn(
                            "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors",
                            index === effectiveHighlightedIndex
                              ? "bg-sky-50 text-slate-950"
                              : "text-slate-700 hover:bg-slate-50"
                          )}
                        >
                          <span
                            className={cn(
                              "grid size-9 shrink-0 place-items-center rounded-xl",
                              index === effectiveHighlightedIndex
                                ? "bg-white text-sky-600 shadow-sm"
                                : "bg-slate-100 text-slate-500"
                            )}
                          >
                            <MapPin className="size-4" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium">
                              {result.stopName}
                            </span>
                            <span className="mt-0.5 block text-xs text-slate-500">
                              Bus stop · Delhi
                            </span>
                          </span>
                          {index === effectiveHighlightedIndex ? (
                            <Check className="size-4 shrink-0 text-sky-600" />
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ul>
                  <div className="border-t border-slate-100 px-4 py-2 text-[11px] text-slate-400">
                    Use ↑ ↓ to navigate · Enter to select
                  </div>
                </>
              ) : null}

              {!isSearching && showNoResults ? (
                <div className="px-4 py-5 text-center">
                  <div className="mx-auto grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-400">
                    <Search className="size-4" />
                  </div>
                  <p className="mt-3 text-sm font-medium text-slate-700">
                    No matching stops
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Try a stop, landmark, or neighbourhood name.
                  </p>
                </div>
              ) : null}
            </div>,
            document.body
          )
        : null}
    </div>
  )
}

export default memo(MapRouteWaypointField)
