import { memo } from "react"
import {
  AlertTriangle,
  ArrowRight,
  Clock3,
  MapPinned,
  Plus,
  Route,
  Sparkles,
  Trash2,
} from "lucide-react"

import type {
  PlannerStatus,
  RouteLegPlan,
  RoutePlanSummary,
  StopSearchResult,
  WaypointField,
} from "@/features/map/domain/types"
import MapRouteWaypointField from "@/features/map/components/sidebar/MapRouteWaypointField"
import { Button } from "@workspace/ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@workspace/ui/components/card"
import { Separator } from "@workspace/ui/components/separator"
import {
  Sidebar,
  SidebarContent,
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
  onWaypointMoveUp: (waypointId: string) => void
  onWaypointMoveDown: (waypointId: string) => void
  onAddWaypoint: () => void
  onClearTrip: () => void
}

function formatMinutes(value: number) {
  if (Number.isInteger(value)) {
    return `${value} min`
  }

  return `${value.toFixed(1)} min`
}

function formatScheduleDeviation(value: number) {
  const absoluteDeviation = Math.abs(value)
  if (absoluteDeviation < 1) {
    return "On time"
  }
  if (value < 0) {
    return `Early ${formatMinutes(absoluteDeviation)}`
  }
  return `Delayed ${formatMinutes(value)}`
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

function getPlannerBanner(plannerStatus: PlannerStatus) {
  switch (plannerStatus) {
    case "routing":
      return {
        tone: "text-sky-700 bg-sky-50 border-sky-100",
        label: "Updating drawn routes between selected bus stops.",
      }
    case "partial":
      return {
        tone: "text-amber-700 bg-amber-50 border-amber-100",
        label: "Some route legs could not be drawn. The rest of the trip is still available.",
      }
    case "error":
      return {
        tone: "text-rose-700 bg-rose-50 border-rose-100",
        label: "Route drawing failed for the selected stops.",
      }
    case "ready":
      return {
        tone: "text-emerald-700 bg-emerald-50 border-emerald-100",
        label: "Routes are drawn from the optimized stop sequence.",
      }
    default:
      return {
        tone: "text-slate-600 bg-slate-50 border-slate-100",
        label: "",
      }
  }
}

function getLegStatusLabel(leg: RouteLegPlan) {
  switch (leg.status) {
    case "loading":
      return "Drawing route"
    case "ready":
      return leg.totalDelayMinutes <= -1
        ? "Early"
        : leg.totalDelayMinutes > 8
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
  onWaypointMoveUp,
  onWaypointMoveDown,
  onAddWaypoint,
  onClearTrip,
}: MapRouteSidebarProps) {
  const plannerBanner = getPlannerBanner(plannerStatus)
  const readyLegCount = routeLegs.filter((leg) => leg.status === "ready").length

  return (
    <Sidebar className="shadow-[20px_0_60px_-44px_rgba(15,23,42,0.45)]">
      <SidebarHeader className="gap-5 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(255,255,255,0.82))]">
        <div className="flex items-start justify-between gap-4">
          <div />

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClearTrip}
            className="shrink-0 rounded-2xl text-slate-600 hover:bg-slate-100"
          >
            <Trash2 className="size-4" />
            Clear trip
          </Button>
        </div>

        {plannerBanner.label ? (
          <div
            className={`rounded-[1.25rem] border px-4 py-3 text-sm leading-6 ${plannerBanner.tone}`}
          >
            {plannerBanner.label}
          </div>
        ) : null}
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup className="gap-4">
          <div className="flex items-center justify-between gap-3 px-1">
            <SidebarGroupLabel className="px-0">Waypoints</SidebarGroupLabel>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onAddWaypoint}
              disabled={!canAddWaypoint}
              className="rounded-2xl border-slate-200 bg-white"
            >
              <Plus className="size-4" />
              Add stop
            </Button>
          </div>

          <SidebarGroupContent>
            {waypoints.map((waypoint, index) => (
              <MapRouteWaypointField
                key={waypoint.id}
                badge={String.fromCharCode(65 + index)}
                query={waypoint.query}
                selectedStop={waypoint.selectedStop}
                canMoveUp={index > 0}
                canMoveDown={index < waypoints.length - 1}
                canRemove={index >= 2}
                onQueryChange={(query) => onWaypointQueryChange(waypoint.id, query)}
                onSelect={(stop) => onWaypointSelect(waypoint.id, stop)}
                onClear={() => onWaypointClear(waypoint.id)}
                onRemove={() => onWaypointRemove(waypoint.id)}
                onMoveUp={() => onWaypointMoveUp(waypoint.id)}
                onMoveDown={() => onWaypointMoveDown(waypoint.id)}
              />
            ))}
          </SidebarGroupContent>
        </SidebarGroup>

        <Separator className="mx-4 w-auto bg-sidebar-border/80" />

        <SidebarGroup>
          <SidebarGroupLabel>Trip Summary</SidebarGroupLabel>
          <SidebarGroupContent>
            <Card variant="glass" padding="sm" className="border-white/70 bg-white/78">
              <CardHeader className="gap-1">
                <CardTitle className="flex items-center gap-2 text-lg text-slate-900">
                  <Sparkles className="size-4 text-sky-600" />
                  Overview
                </CardTitle>
                <CardDescription>
                  {readyLegCount > 0
                    ? `${readyLegCount} route leg${readyLegCount === 1 ? "" : "s"} currently drawn on the map.`
                    : "Add two or more stops to start drawing route legs."}
                </CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-slate-950 px-4 py-3 text-white">
                  <p className="text-[11px] font-medium tracking-[0.16em] text-white/60 uppercase">
                    ETA
                  </p>
                  <p className="mt-2 text-2xl font-semibold tracking-[-0.04em]">
                    {summary ? formatMinutes(summary.totalEtaMinutes) : "--"}
                  </p>
                </div>
                <div className="rounded-2xl bg-slate-100 px-4 py-3 text-slate-900">
                  <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                    Arrival
                  </p>
                  <p className="mt-2 text-lg font-semibold tracking-[-0.03em]">
                    {summary ? formatArrivalTime(summary.predictedArrivalUnix) : "--"}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                    Schedule
                  </p>
                  <p className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-900">
                    {summary ? formatScheduleDeviation(summary.totalDelayMinutes) : "--"}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                    Transfers
                  </p>
                  <p className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-900">
                    {summary ? summary.transferCount : "--"}
                  </p>
                </div>
                <div className="col-span-2 rounded-2xl border border-slate-200 bg-white px-4 py-3">
                  <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                    Total Wait
                  </p>
                  <p className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-900">
                    {summary ? formatMinutes(summary.totalWaitMinutes) : "--"}
                  </p>
                </div>
              </CardContent>
            </Card>
          </SidebarGroupContent>
        </SidebarGroup>

        <Separator className="mx-4 w-auto bg-sidebar-border/80" />

        <SidebarGroup className="pb-8">
          <SidebarGroupLabel>Route Legs</SidebarGroupLabel>
          <SidebarGroupContent>
            {routeLegs.length === 0 ? (
              <Card variant="glass" padding="sm" className="border-white/70 bg-white/78">
                <CardContent className="flex items-start gap-3 text-sm text-slate-600">
                  <MapPinned className="mt-0.5 size-4 text-sky-600" />
                  Drawn routes appear here once at least two bus stops are selected.
                </CardContent>
              </Card>
            ) : (
              routeLegs.map((leg) => (
                <Card
                  key={leg.id}
                  variant="glass"
                  padding="sm"
                  className="border-white/70 bg-white/78"
                >
                  <CardHeader className="gap-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-lg text-slate-900">
                          <Route className="size-4 text-sky-600" />
                          {leg.fromBadge} <ArrowRight className="size-4 text-slate-400" /> {leg.toBadge}
                        </CardTitle>
                        <CardDescription className="mt-1">
                          {leg.fromStop?.stopName ?? "Select a stop"} to{" "}
                          {leg.toStop?.stopName ?? "select a stop"}
                        </CardDescription>
                      </div>
                      <span
                        className={cn(
                          "rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-[0.12em] uppercase",
                          leg.status === "ready"
                            ? "bg-emerald-50 text-emerald-700"
                            : leg.status === "loading"
                              ? "bg-sky-50 text-sky-700"
                              : leg.status === "error"
                                ? "bg-rose-50 text-rose-700"
                                : "bg-slate-100 text-slate-600"
                        )}
                      >
                        {getLegStatusLabel(leg)}
                      </span>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-3">
                    {leg.status === "error" ? (
                      <div className="flex items-start gap-2 rounded-2xl border border-rose-100 bg-rose-50 px-3 py-2.5 text-sm text-rose-700">
                        <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                        <span>{leg.errorMessage ?? "This leg could not be routed."}</span>
                      </div>
                    ) : null}

                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                        <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                          ETA
                        </p>
                        <p className="mt-1.5 text-base font-semibold text-slate-900">
                          {leg.status === "ready" ? formatMinutes(leg.totalEtaMinutes) : "--"}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                        <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                          Schedule
                        </p>
                        <p className="mt-1.5 text-base font-semibold text-slate-900">
                          {leg.status === "ready"
                            ? formatScheduleDeviation(leg.totalDelayMinutes)
                            : "--"}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                        <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                          Boarding Wait
                        </p>
                        <p className="mt-1.5 text-base font-semibold text-slate-900">
                          {leg.status === "ready" ? formatMinutes(leg.waitMinutes) : "--"}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
                        <p className="text-[11px] font-medium tracking-[0.16em] text-slate-500 uppercase">
                          Bus Routes
                        </p>
                        <p className="mt-1.5 line-clamp-2 text-sm font-medium text-slate-900">
                          {leg.status === "ready" && leg.segments.length > 0
                            ? Array.from(new Set(leg.segments.map((segment) => segment.routeId))).join(", ")
                            : "--"}
                        </p>
                      </div>
                    </div>

                    {leg.status === "ready" ? (
                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <Clock3 className="size-3.5" />
                        Path includes {leg.responseStops.length} routed stop
                        {leg.responseStops.length === 1 ? "" : "s"}.
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              ))
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}

export default memo(MapRouteSidebar)
