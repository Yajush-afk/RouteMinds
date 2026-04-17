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
import { memo } from "react"
import { ArrowRight, LogOut, Plus, Trash2 } from "lucide-react"

import type {
  PlannerStatus,
  RouteLegPlan,
  RoutePlanSummary,
  StopSearchResult,
  WaypointField,
} from "@/features/map/domain/types"
import MapRouteWaypointField from "@/features/map/components/sidebar/MapRouteWaypointField"
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@workspace/ui/components/avatar"
import { Button } from "@workspace/ui/components/button"
import { Separator } from "@workspace/ui/components/separator"
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
  onWaypointReorder: (activeWaypointId: string, overWaypointId: string) => void
  onAddWaypoint: () => void
  onClearTrip: () => void
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
  onWaypointReorder,
  onAddWaypoint,
  onClearTrip,
  user,
  onSignOut,
}: MapRouteSidebarProps) {
  const readyLegCount = routeLegs.filter((leg) => leg.status === "ready").length
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

      <SidebarContent className="min-w-0 overflow-x-hidden overscroll-x-none">
        <SidebarGroup className="relative z-20 gap-4 overflow-visible">
          <div className="flex items-center justify-between gap-3 px-1">
            <SidebarGroupLabel className="px-0">Stops</SidebarGroupLabel>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onAddWaypoint}
                disabled={!canAddWaypoint}
                className="rounded-xl border-slate-200 bg-white"
              >
                <Plus className="size-4" />
                Add stop
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClearTrip}
                className="rounded-xl text-slate-600 hover:bg-slate-100"
              >
                <Trash2 className="size-4" />
                Clear trip
              </Button>
            </div>
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
                <div className="space-y-3 overflow-x-hidden">
                  {waypoints.map((waypoint, index) => (
                    <MapRouteWaypointField
                      key={waypoint.id}
                      waypointId={waypoint.id}
                      badge={String.fromCharCode(65 + index)}
                      query={waypoint.query}
                      selectedStop={waypoint.selectedStop}
                      canRemove={index >= 2}
                      onQueryChange={(query) =>
                        onWaypointQueryChange(waypoint.id, query)
                      }
                      onSelect={(stop) => onWaypointSelect(waypoint.id, stop)}
                      onClear={() => onWaypointClear(waypoint.id)}
                      onRemove={() => onWaypointRemove(waypoint.id)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
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
          <SidebarGroupLabel>Route Legs</SidebarGroupLabel>
          <SidebarGroupContent>
            {routeLegs.length === 0 ? (
              <div className="rounded-2xl border border-slate-200/80 bg-white/84 px-3 py-3 text-sm text-slate-600">
                Add at least two selected stops to view route leg details.
              </div>
            ) : (
              routeLegs.map((leg) => (
                <div
                  key={leg.id}
                  className="rounded-2xl border border-slate-200/80 bg-white/84 px-3 py-3"
                >
                  <p className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                    {leg.fromBadge}
                    <ArrowRight className="size-3.5 text-slate-400" />
                    {leg.toBadge}
                  </p>
                  <div className="mt-3 space-y-2">
                    <DetailRow
                      label="Stops"
                      value={`${leg.fromStop?.stopName ?? "Select a stop"} to ${leg.toStop?.stopName ?? "select a stop"}`}
                    />
                    <DetailRow label="Status" value={getLegStatusLabel(leg)} />
                    <DetailRow
                      label="ETA"
                      value={
                        leg.status === "ready"
                          ? formatMinutes(leg.totalEtaMinutes)
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
                      label="Wait"
                      value={
                        leg.status === "ready"
                          ? formatMinutes(leg.waitMinutes)
                          : "--"
                      }
                    />
                    <DetailRow
                      label="Routes"
                      value={
                        leg.status === "ready" && leg.segments.length > 0
                          ? Array.from(
                              new Set(
                                leg.segments.map((segment) => segment.routeId)
                              )
                            ).join(", ")
                          : "--"
                      }
                    />
                    <DetailRow
                      label="Routed Stops"
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
                          leg.errorMessage ?? "This leg could not be routed."
                        }
                        valueTone="text-rose-700"
                      />
                    ) : null}
                  </div>
                </div>
              ))
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

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
          size="sm"
          onClick={() => {
            void onSignOut()
          }}
          className="rounded-xl text-slate-600 hover:bg-rose-50 hover:text-rose-700"
        >
          <LogOut className="size-4" />
          Sign out
        </Button>
      </SidebarFooter>
    </Sidebar>
  )
}

export default memo(MapRouteSidebar)
