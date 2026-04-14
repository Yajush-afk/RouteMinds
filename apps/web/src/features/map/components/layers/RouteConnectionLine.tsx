import { memo, useMemo } from "react"

import { Layer, Source } from "react-map-gl/maplibre"
import type { LineLayerSpecification } from "maplibre-gl"

import type { LngLat } from "@/features/map/domain/types"

type RouteConnectionLineProps = {
  origin: LngLat
  destination: LngLat
}

function buildCurve(origin: LngLat, destination: LngLat) {
  const deltaLng = destination.lng - origin.lng
  const deltaLat = destination.lat - origin.lat
  const distance = Math.hypot(deltaLng, deltaLat)

  if (distance === 0) {
    return [
      [origin.lng, origin.lat],
      [destination.lng, destination.lat],
    ]
  }

  const midpoint = {
    lng: (origin.lng + destination.lng) / 2,
    lat: (origin.lat + destination.lat) / 2,
  }

  const perpendicular = {
    lng: -deltaLat / distance,
    lat: deltaLng / distance,
  }

  const curveStrength = Math.min(distance * 0.18, 0.018)
  const controlPoint = {
    lng: midpoint.lng + perpendicular.lng * curveStrength,
    lat: midpoint.lat + perpendicular.lat * curveStrength,
  }

  return Array.from({ length: 33 }, (_, index) => {
    const t = index / 32
    const inverseT = 1 - t

    const lng =
      inverseT * inverseT * origin.lng +
      2 * inverseT * t * controlPoint.lng +
      t * t * destination.lng
    const lat =
      inverseT * inverseT * origin.lat +
      2 * inverseT * t * controlPoint.lat +
      t * t * destination.lat

    return [lng, lat]
  })
}

const LINE_LAYER: Omit<LineLayerSpecification, "source"> = {
  id: "route-connection-line",
  type: "line",
  layout: {
    "line-cap": "round",
    "line-join": "round",
  },
  paint: {
    "line-color": "#0f172a",
    "line-width": 3,
    "line-opacity": 0.72,
    "line-dasharray": [0.1, 2.1],
    "line-blur": 0.1,
  },
}

function RouteConnectionLine({
  origin,
  destination,
}: RouteConnectionLineProps) {
  const data = useMemo(
    () => ({
      type: "Feature" as const,
      properties: {},
      geometry: {
        type: "LineString" as const,
        coordinates: buildCurve(origin, destination),
      },
    }),
    [destination, origin]
  )

  return (
    <Source id="route-connection-source" type="geojson" data={data}>
      <Layer {...LINE_LAYER} />
    </Source>
  )
}

export default memo(RouteConnectionLine)
