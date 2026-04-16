import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { memo, useEffect, useRef, useState } from "react"
import type { KeyboardEvent } from "react"
import { GripVertical, LoaderCircle, Search, Trash2, X } from "lucide-react"

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
  onQueryChange: (nextQuery: string) => void
  onSelect: (stop: StopSearchResult) => void
  onClear: () => void
  onRemove: () => void
}

function MapRouteWaypointField({
  waypointId,
  badge,
  query,
  selectedStop,
  canRemove,
  onQueryChange,
  onSelect,
  onClear,
  onRemove,
}: MapRouteWaypointFieldProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
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
      if (!containerRef.current?.contains(event.target as Node)) {
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
      : highlightedIndex < 0 || highlightedIndex >= results.length
        ? 0
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
        "relative z-0 rounded-[1.25rem] border border-sidebar-border/90 bg-white/75 p-2.5 shadow-[0_14px_36px_-26px_rgba(15,23,42,0.45)] backdrop-blur transition-[border-color,box-shadow,background-color]",
        showDropdown ? "z-50" : undefined,
        isOver ? "border-sky-300 bg-sky-50/55" : undefined,
        isDragging ? "z-[70] opacity-90 shadow-xl" : undefined
      )}
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-3.5 size-3.5 -translate-y-1/2 text-slate-400" />
            <Input
              value={query}
              placeholder="Search bus stop"
              autoComplete="off"
              onFocus={() => setIsOpen(true)}
              onChange={(event) => {
                onQueryChange(event.target.value)
                setIsOpen(true)
              }}
              onKeyDown={handleKeyDown}
              className="h-10 rounded-xl border-0 bg-white pr-10 pl-10 shadow-none focus-visible:border-0 focus-visible:ring-0"
            />
            {query ? (
              <button
                type="button"
                onClick={onClear}
                className="absolute top-1/2 right-2.5 grid size-6 -translate-y-1/2 place-items-center rounded-md text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                aria-label={`Clear waypoint ${badge}`}
              >
                <X className="size-3.5" />
              </button>
            ) : null}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1 pt-0.5">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label={`Reorder waypoint ${badge}`}
            className="cursor-grab touch-none rounded-lg text-slate-500 select-none hover:bg-slate-100 active:cursor-grabbing"
            {...attributes}
            {...listeners}
          >
            <GripVertical className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onRemove}
            disabled={!canRemove}
            aria-label={`Remove waypoint ${badge}`}
            className="rounded-lg text-slate-500 hover:bg-rose-50 hover:text-rose-600"
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      </div>

      {showDropdown ? (
        <div className="absolute inset-x-3 top-full z-[80] mt-2 overflow-hidden rounded-[1.35rem] border border-slate-200 bg-white shadow-xl">
          {isSearching ? (
            <div className="flex items-center gap-2 px-4 py-3 text-sm text-slate-600">
              <LoaderCircle className="size-4 animate-spin text-slate-500" />
              Searching bus stops...
            </div>
          ) : null}

          {!isSearching && errorMessage ? (
            <div className="px-4 py-3 text-sm text-rose-600">
              {errorMessage}
            </div>
          ) : null}

          {!isSearching && !errorMessage && results.length > 0 ? (
            <ul className="max-h-[10.5rem] overflow-y-auto overscroll-contain">
              {results.map((result, index) => (
                <li
                  key={`${result.stopId}-${result.stopName}`}
                  className={cn(
                    index > 0 ? "border-t border-slate-100" : undefined
                  )}
                >
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleSelect(result)}
                    className={cn(
                      "flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors",
                      index === effectiveHighlightedIndex
                        ? "bg-sky-50 text-slate-900"
                        : "text-slate-700 hover:bg-slate-50"
                    )}
                  >
                    <span className="truncate text-sm font-medium">
                      {result.stopName}
                    </span>
                    <span className="text-xs text-slate-500">
                      Stop ID {result.stopId}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          {!isSearching && showNoResults ? (
            <div className="px-4 py-3 text-sm text-slate-500">
              No bus stops matched this search.
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export default memo(MapRouteWaypointField)
