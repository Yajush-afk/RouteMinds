import type { StopSearchResult } from "@/features/map/domain/types"

const MOCK_STOP_VARIANTS = [
  { suffix: "Chowk", latOffset: 0, lngOffset: 0 },
  { suffix: "Market Gate", latOffset: 0.006, lngOffset: -0.004 },
  { suffix: "Metro Link", latOffset: -0.005, lngOffset: 0.007 },
  { suffix: "Community Centre", latOffset: 0.009, lngOffset: 0.006 },
  { suffix: "Main Road", latOffset: -0.008, lngOffset: -0.006 },
  { suffix: "Depot", latOffset: 0.003, lngOffset: 0.011 },
] as const

function toDisplayQuery(query: string) {
  return query
    .trim()
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ")
}

export async function searchMockStops(
  query: string,
  options: { limit?: number; signal?: AbortSignal } = {}
): Promise<StopSearchResult[]> {
  if (options.signal?.aborted) {
    throw new DOMException("The request was aborted.", "AbortError")
  }

  const displayQuery = toDisplayQuery(query)
  const normalizedId = query
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")

  if (!displayQuery) {
    return []
  }

  return MOCK_STOP_VARIANTS.slice(0, options.limit ?? 8).map(
    (variant, index) => ({
      stopId: `DEMO-${normalizedId || "STOP"}-${index + 1}`,
      stopName: `${displayQuery} ${variant.suffix}`,
      position: {
        lat: 28.6139 + variant.latOffset,
        lng: 77.209 + variant.lngOffset,
      },
      matchScore: 1 - index * 0.08,
    })
  )
}
