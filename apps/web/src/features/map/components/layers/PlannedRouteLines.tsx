import { memo, useMemo } from "react"

import { Layer, Source } from "react-map-gl/maplibre"
import type { LineLayerSpecification } from "maplibre-gl"

import type { RouteLegPlan } from "@/features/map/domain/types"

type PlannedRouteLinesProps = {
  routeLegs: RouteLegPlan[]
}

const ROUTE_LINE_LAYER: Omit<LineLayerSpecification, "source"> = {
  id: "planned-route-lines",
  type: "line",
  layout: {
    "line-cap": "round",
    "line-join": "round",
  },
  paint: {
    "line-width": 4,
    "line-opacity": 0.88,
    "line-color": [
      "match",
      ["get", "legIndex"],
      0,
      "#0f766e",
      1,
      "#0369a1",
      2,
      "#7c3aed",
      3,
      "#ea580c",
      4,
      "#dc2626",
      5,
      "#16a34a",
      6,
      "#2563eb",
      "#0f172a",
    ],
  },
}

function PlannedRouteLines({ routeLegs }: PlannedRouteLinesProps) {
  const data = useMemo(
    () => ({
      type: "FeatureCollection" as const,
      features: routeLegs
        .filter(
          (leg) => leg.status === "ready" && leg.lineCoordinates.length >= 2
        )
        .map((leg, legIndex) => ({
          type: "Feature" as const,
          properties: {
            id: leg.id,
            legIndex,
          },
          geometry: {
            type: "LineString" as const,
            coordinates: leg.lineCoordinates,
          },
        })),
    }),
    [routeLegs]
  )

  if (data.features.length === 0) {
    return null
  }

  return (
    <Source id="planned-route-source" type="geojson" data={data}>
      <Layer {...ROUTE_LINE_LAYER} />
    </Source>
  )
}

export default memo(PlannedRouteLines)
