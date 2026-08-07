import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type Modifier,
} from "@dnd-kit/core"
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { memo, useEffect, useRef, useState } from "react"
import { ArrowRight, LogOut, Plus, RotateCcw, X } from "lucide-react"

import type {
  PlannerStatus,
  RouteLegPlan,
  RoutePlanSummary,
  StopSearchResult,
  WaypointField,
} from "@/features/map/domain/types"
import MapRouteWaypointField from "@/features/map/components/sidebar/MapRouteWaypointField"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@workspace/ui/components/avatar"
import { Button } from "@workspace/ui/components/button"
import { Separator } from "@workspace/ui/components/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@workspace/ui/components/tooltip"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
} from "@workspace/ui/components/sidebar"
import { cn } from "@workspace/ui/lib/utils"

type MapRouteSidebarProps = {
  waypoints: WaypointField[]
  routeLegs: RouteLegPlan[]
  summary: RoutePlanSummary | null
  plannerStatus: PlannerStatus
  canAddWaypoint: boolean
  onWaypointQueryChange: (waypointId: string, query: string) => void
  onWaypointSelect: (waypointId: string, stop: StopSearchResult) => void
  onWaypointClear: (waypointId: string) => void
  onWaypointRemove: (waypointId: string) => void
  onWaypointRestore: (waypoint: WaypointField, index: number) => void
  onWaypointReorder: (activeWaypointId: string, overWaypointId: string) => void
  onAddWaypoint: () => void
  onClearTrip: () => void
  onTripRestore: (waypoints: WaypointField[]) => void
  user: {
    email?: string
    name?: string
    picture?: string
  } | null
  onSignOut: () => Promise<void>
}

type DetailRowProps = {
  label: string
  value: string
  valueTone?: string
}

type RemovedWaypoint = {
  waypoint: WaypointField
  index: number
}

const UNDO_REMOVE_DURATION_MS = 5_000

const verticalOnlyDragModifier: Modifier = ({ transform }) => ({
  ...transform,
  x: 0,
})

function formatMinutes(value: number) {
  if (Number.isInteger(value)) {
    return `${value} min`
  }

  return `${value.toFixed(1)} min`
}

function formatArrivalTime(timestamp: number | null) {
  if (timestamp === null) {
    return "Not available"
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(timestamp * 1000))
}

function getPlannerStatusLabel(plannerStatus: PlannerStatus) {
  switch (plannerStatus) {
    case "routing":
      return "Updating routes"
    case "partial":
      return "Partially available"
    case "error":
      return "Route unavailable"
    case "ready":
      return "Ready"
    default:
      return "Waiting for stops"
  }
}

function getLegStatusLabel(leg: RouteLegPlan) {
  switch (leg.status) {
    case "loading":
      return "Drawing route"
    case "ready":
      return leg.totalDelayMinutes > 8
        ? "Heavy delay"
        : leg.totalDelayMinutes > 3
          ? "Moderate delay"
          : "On time"
    case "error":
      return "Route unavailable"
    default:
      return "Waiting for stops"
  }
}

function getLegRoutes(leg: RouteLegPlan) {
  if (leg.status !== "ready" || leg.segments.length === 0) {
    return null
  }

  return Array.from(new Set(leg.segments.map((segment) => segment.routeId)))
}

function getAvatarFallback(name?: string, email?: string) {
  const words = (name ?? "")
    .trim()
    .split(/\s+/)
    .map((word) => word.replace(/[^a-z0-9]/gi, ""))
    .filter(Boolean)

  if (words.length >= 2) {
    return `${words[0][0]}${words[1][0]}`.slice(0, 2).toUpperCase()
  }

  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase()
  }

  const emailLocalPart = (email ?? "")
    .split("@")[0]
    ?.replace(/[^a-z0-9]/gi, "")
    .trim()

  if (emailLocalPart) {
    return emailLocalPart.slice(0, 2).toUpperCase()
  }

  return "RM"
}

function DetailRow({ label, value, valueTone }: DetailRowProps) {
  return (
    <div className="flex min-w-0 items-start justify-between gap-4">
      <span className="shrink-0 text-xs font-medium tracking-[0.12em] text-slate-500 uppercase">
        {label}
      </span>
      <span
        className={cn(
          "max-w-[65%] min-w-0 text-right text-sm font-medium break-words text-slate-900",
          valueTone
        )}
      >
        {value}
      </span>
    </div>
  )
}

function MapRouteSidebar({
  waypoints,
  routeLegs,
  summary,
  plannerStatus,
  canAddWaypoint,
  onWaypointQueryChange,
  onWaypointSelect,
  onWaypointClear,
  onWaypointRemove,
  onWaypointRestore,
  onWaypointReorder,
  onAddWaypoint,
  onClearTrip,
  onTripRestore,
  user,
  onSignOut,
}: MapRouteSidebarProps) {
  const [removedWaypoint, setRemovedWaypoint] =
    useState<RemovedWaypoint | null>(null)
  const [resetWaypoints, setResetWaypoints] = useState<WaypointField[] | null>(
    null
  )
  const undoTimeoutRef = useRef<number | null>(null)
  const readyLegCount = routeLegs.filter((leg) => leg.status === "ready").length
  const hasTripContent =
    waypoints.length > 2 ||
    waypoints.some((waypoint) => waypoint.query || waypoint.selectedStop)
  const avatarFallback = getAvatarFallback(user?.name, user?.email)
  const avatarTitle = user?.name ?? user?.email ?? "RouteMinds user"
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  useEffect(() => {
    return () => {
      if (undoTimeoutRef.current !== null) {
        window.clearTimeout(undoTimeoutRef.current)
      }
    }
  }, [])

  function focusWaypoint(waypointId: string | undefined) {
    if (!waypointId) {
      return
    }

    window.requestAnimationFrame(() => {
      document.getElementById(`waypoint-input-${waypointId}`)?.focus()
    })
  }

  function handleWaypointRemove(waypoint: WaypointField, index: number) {
    const nextFocusId = waypoints[index + 1]?.id ?? waypoints[index - 1]?.id

    onWaypointRemove(waypoint.id)
    setRemovedWaypoint({ waypoint, index })
    setResetWaypoints(null)
    focusWaypoint(nextFocusId)

    if (undoTimeoutRef.current !== null) {
      window.clearTimeout(undoTimeoutRef.current)
    }

    undoTimeoutRef.current = window.setTimeout(() => {
      setRemovedWaypoint(null)
      undoTimeoutRef.current = null
    }, UNDO_REMOVE_DURATION_MS)
  }

  function handleUndoRemove() {
    if (!removedWaypoint) {
      return
    }

    onWaypointRestore(removedWaypoint.waypoint, removedWaypoint.index)
    focusWaypoint(removedWaypoint.waypoint.id)
    setRemovedWaypoint(null)

    if (undoTimeoutRef.current !== null) {
      window.clearTimeout(undoTimeoutRef.current)
      undoTimeoutRef.current = null
    }
  }

  function dismissRemoveNotice() {
    setRemovedWaypoint(null)

    if (undoTimeoutRef.current !== null) {
      window.clearTimeout(undoTimeoutRef.current)
      undoTimeoutRef.current = null
    }
  }

  function handleResetTrip() {
    if (!hasTripContent) {
      return
    }

    setResetWaypoints(waypoints)
    setRemovedWaypoint(null)
    onClearTrip()
    focusWaypoint(waypoints[0]?.id)

    if (undoTimeoutRef.current !== null) {
      window.clearTimeout(undoTimeoutRef.current)
    }

    undoTimeoutRef.current = window.setTimeout(() => {
      setResetWaypoints(null)
      undoTimeoutRef.current = null
    }, UNDO_REMOVE_DURATION_MS)
  }

  function handleUndoReset() {
    if (!resetWaypoints) {
      return
    }

    onTripRestore(resetWaypoints)
    focusWaypoint(resetWaypoints[0]?.id)
    setResetWaypoints(null)

    if (undoTimeoutRef.current !== null) {
      window.clearTimeout(undoTimeoutRef.current)
      undoTimeoutRef.current = null
    }
  }

  function dismissResetNotice() {
    setResetWaypoints(null)

    if (undoTimeoutRef.current !== null) {
      window.clearTimeout(undoTimeoutRef.current)
      undoTimeoutRef.current = null
    }
  }

  function handleWaypointDragEnd(event: DragEndEvent) {
    const { active, over } = event

    if (!over || active.id === over.id) {
      return
    }

    onWaypointReorder(String(active.id), String(over.id))
  }

  return (
    <Sidebar className="pointer-events-auto absolute top-4 bottom-4 left-4 z-40 h-auto max-w-[var(--sidebar-width)] min-w-[var(--sidebar-width)] overflow-hidden rounded-2xl border border-white/70 bg-white/88 p-2 shadow-[0_30px_95px_-48px_rgba(15,23,42,0.48)] backdrop-blur-xl">
      <SidebarHeader className="gap-0 border-b border-sidebar-border/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(255,255,255,0.88))] px-4 py-3">
        <div className="flex w-full items-center justify-center gap-2">
          <img
            src="/favicon.svg"
            alt=""
            className="size-6"
            aria-hidden="true"
          />
          <span className="text-lg font-semibold tracking-tight text-slate-900">
            RouteMinds
          </span>
        </div>
      </SidebarHeader>

      <SidebarContent className="subtle-scrollbar min-w-0 overflow-x-hidden overscroll-x-none">
        <SidebarGroup className="relative z-20 gap-4 overflow-visible">
          <div className="flex items-center justify-between gap-3 px-1">
            <SidebarGroupLabel className="px-0">Stops</SidebarGroupLabel>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={handleResetTrip}
                  disabled={!hasTripContent}
                  aria-label="Reset trip"
                  className="rounded-xl text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                >
                  <RotateCcw className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left" sideOffset={6}>
                Reset trip
              </TooltipContent>
            </Tooltip>
          </div>

          <SidebarGroupContent className="overflow-visible">
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              modifiers={[verticalOnlyDragModifier]}
              onDragEnd={handleWaypointDragEnd}
            >
              <SortableContext
                items={waypoints.map((waypoint) => waypoint.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="space-y-3 overflow-x-hidden px-0.5 py-0.5">
                  {waypoints.map((waypoint, index) => (
                    <MapRouteWaypointField
                      key={waypoint.id}
                      waypointId={waypoint.id}
                      badge={String.fromCharCode(65 + index)}
                      query={waypoint.query}
                      selectedStop={waypoint.selectedStop}
                      canRemove={index >= 2}
                      isFirst={index === 0}
                      isLast={index === waypoints.length - 1}
                      onQueryChange={(query) =>
                        onWaypointQueryChange(waypoint.id, query)
                      }
                      onSelect={(stop) => onWaypointSelect(waypoint.id, stop)}
                      onClear={() => onWaypointClear(waypoint.id)}
                      onRemove={() => handleWaypointRemove(waypoint, index)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>

            <div className="flex justify-center pt-1">
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={onAddWaypoint}
                disabled={!canAddWaypoint}
                aria-label="Add another stop"
                className="size-9 rounded-full border-slate-200 bg-white text-slate-500 shadow-sm hover:border-slate-300 hover:bg-slate-100 hover:text-slate-800 focus-visible:border-slate-300 focus-visible:ring-slate-200"
              >
                <Plus className="size-4" />
              </Button>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>

        <Separator className="mx-4 w-auto bg-sidebar-border/80" />

        <SidebarGroup className="relative z-0">
          <SidebarGroupLabel>Trip Summary</SidebarGroupLabel>
          <SidebarGroupContent className="rounded-2xl border border-slate-200/80 bg-white/84 px-3 py-3">
            <DetailRow
              label="Status"
              value={getPlannerStatusLabel(plannerStatus)}
            />
            <DetailRow label="Route legs" value={String(readyLegCount)} />
            <DetailRow
              label="ETA"
              value={summary ? formatMinutes(summary.totalEtaMinutes) : "--"}
            />
            <DetailRow
              label="Arrival"
              value={
                summary ? formatArrivalTime(summary.predictedArrivalUnix) : "--"
              }
            />
            <DetailRow
              label="Delay"
              value={summary ? formatMinutes(summary.totalDelayMinutes) : "--"}
            />
            <DetailRow
              label="Transfers"
              value={summary ? String(summary.transferCount) : "--"}
            />
            <DetailRow
              label="Total Wait"
              value={summary ? formatMinutes(summary.totalWaitMinutes) : "--"}
            />
          </SidebarGroupContent>
        </SidebarGroup>

        <Separator className="mx-4 w-auto bg-sidebar-border/80" />

        <SidebarGroup className="relative z-0 pb-6">
          <SidebarGroupLabel>Trip Details</SidebarGroupLabel>
          <SidebarGroupContent>
            {routeLegs.length === 0 ? (
              <div className="rounded-2xl border border-slate-200/80 bg-white/84 px-3 py-3 text-sm text-slate-600">
                Select at least two stops to see your trip details.
              </div>
            ) : (
              <Accordion className="gap-2">
                {routeLegs.map((leg) => {
                  const routes = getLegRoutes(leg)

                  return (
                    <AccordionItem
                      key={leg.id}
                      value={leg.id}
                      className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white/84 px-3 data-open:border-slate-300 data-open:shadow-sm"
                    >
                      <AccordionTrigger className="items-center gap-3 py-3 hover:no-underline">
                        <span className="flex min-w-0 flex-1 items-center gap-3">
                          <span className="flex shrink-0 items-center gap-1.5 text-xs font-bold text-slate-700">
                            <span className="grid size-6 place-items-center rounded-full bg-slate-100">
                              {leg.fromBadge}
                            </span>
                            <ArrowRight className="size-3 text-slate-400" />
                            <span className="grid size-6 place-items-center rounded-full bg-slate-800 text-white">
                              {leg.toBadge}
                            </span>
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-semibold text-slate-900">
                              {leg.fromStop?.stopName ?? "Select a stop"}
                              <span className="px-1.5 text-slate-400">to</span>
                              {leg.toStop?.stopName ?? "select a stop"}
                            </span>
                            <span className="mt-1 block truncate text-xs font-normal text-slate-500">
                              {routes?.length
                                ? `Bus ${routes.join(", ")}`
                                : getLegStatusLabel(leg)}
                              {leg.status === "ready"
                                ? ` · ${formatMinutes(leg.totalEtaMinutes)}`
                                : ""}
                            </span>
                          </span>
                        </span>
                      </AccordionTrigger>
                      <AccordionContent className="border-t border-slate-100 pt-3 pb-3">
                        <div className="space-y-2.5">
                          <DetailRow
                            label="Status"
                            value={getLegStatusLabel(leg)}
                          />
                          <DetailRow
                            label="Travel time"
                            value={
                              leg.status === "ready"
                                ? formatMinutes(leg.totalEtaMinutes)
                                : "--"
                            }
                          />
                          <DetailRow
                            label="Wait"
                            value={
                              leg.status === "ready"
                                ? formatMinutes(leg.waitMinutes)
                                : "--"
                            }
                          />
                          <DetailRow
                            label="Delay"
                            value={
                              leg.status === "ready"
                                ? formatMinutes(leg.totalDelayMinutes)
                                : "--"
                            }
                          />
                          <DetailRow
                            label="Transfers"
                            value={
                              leg.status === "ready"
                                ? String(leg.transferCount)
                                : "--"
                            }
                          />
                          <DetailRow
                            label="Bus routes"
                            value={routes?.join(", ") ?? "--"}
                          />
                          <DetailRow
                            label="Stops"
                            value={
                              leg.status === "ready"
                                ? String(leg.responseStops.length)
                                : "--"
                            }
                          />
                          {leg.status === "error" ? (
                            <DetailRow
                              label="Error"
                              value={
                                leg.errorMessage ??
                                "This section could not be routed."
                              }
                              valueTone="text-rose-700"
                            />
                          ) : null}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  )
                })}
              </Accordion>
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {removedWaypoint ? (
        <div
          role="status"
          className="absolute right-4 bottom-[4.75rem] left-4 z-100 flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-950 px-3 py-2.5 text-white shadow-xl"
        >
          <p className="min-w-0 flex-1 truncate text-sm">
            {removedWaypoint.waypoint.selectedStop?.stopName ?? "Stop"} removed
          </p>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleUndoRemove}
            className="shrink-0 rounded-lg text-white hover:bg-white/15 hover:text-white"
          >
            <RotateCcw className="size-3.5" />
            Undo
          </Button>
          <button
            type="button"
            onClick={dismissRemoveNotice}
            className="grid size-7 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-white/15 hover:text-white"
            aria-label="Dismiss removal notice"
          >
            <X className="size-3.5" />
          </button>
        </div>
      ) : null}

      {resetWaypoints ? (
        <div
          role="status"
          className="absolute right-4 bottom-[4.75rem] left-4 z-100 flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-950 px-3 py-2.5 text-white shadow-xl"
        >
          <p className="min-w-0 flex-1 truncate text-sm">Trip reset</p>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleUndoReset}
            className="shrink-0 rounded-lg text-white hover:bg-white/15 hover:text-white"
          >
            <RotateCcw className="size-3.5" />
            Undo
          </Button>
          <button
            type="button"
            onClick={dismissResetNotice}
            className="grid size-7 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-white/15 hover:text-white"
            aria-label="Dismiss reset notice"
          >
            <X className="size-3.5" />
          </button>
        </div>
      ) : null}

      <SidebarFooter className="flex items-center justify-between gap-3 border-t border-sidebar-border/80 bg-white/84 px-4 py-3">
        <Avatar className="size-9 ring-1 ring-slate-200/80">
          <AvatarImage src={user?.picture} alt={avatarTitle} />
          <AvatarFallback className="bg-slate-100 text-xs font-semibold tracking-[0.12em] text-slate-700">
            {avatarFallback}
          </AvatarFallback>
        </Avatar>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => {
            void onSignOut()
          }}
          aria-label="Sign out"
          className="rounded-xl text-slate-500 hover:bg-slate-100 hover:text-slate-800"
        >
          <LogOut className="size-5" />
        </Button>
      </SidebarFooter>
    </Sidebar>
  )
}

export default memo(MapRouteSidebar)
