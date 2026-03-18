import { DELHI_POLYGON_LNGLAT } from "@/data/delhi-polygon"
import { DELHI_ONLY_ALERT_MESSAGE } from "./mapDefaults"
import type { LngLat } from "./types"

function isPointOnSegment(
  point: [number, number],
  start: [number, number],
  end: [number, number]
) {
  const [px, py] = point
  const [x1, y1] = start
  const [x2, y2] = end
  const cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)

  if (Math.abs(cross) > Number.EPSILON) {
    return false
  }

  const dot = (px - x1) * (px - x2) + (py - y1) * (py - y2)
  return dot <= 0
}

function isPointInRing(
  point: [number, number],
  ring: ReadonlyArray<[number, number]>
) {
  let inside = false

  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]

    if (isPointOnSegment(point, [xi, yi], [xj, yj])) {
      return true
    }

    const intersects =
      yi > point[1] !== yj > point[1] &&
      point[0] < ((xj - xi) * (point[1] - yi)) / (yj - yi) + xi

    if (intersects) {
      inside = !inside
    }
  }

  return inside
}

export function isSelectableLocation(position: LngLat) {
  return isPointInRing([position.lng, position.lat], DELHI_POLYGON_LNGLAT)
}

export function getLocationRejectionReason(position: LngLat) {
  if (isSelectableLocation(position)) {
    return null
  }

  return DELHI_ONLY_ALERT_MESSAGE
}
