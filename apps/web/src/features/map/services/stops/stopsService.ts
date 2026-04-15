import { apiFetch } from "@/lib/api/client"

import type { StopSearchResult } from "@/features/map/domain/types"

type StopSearchResponse = {
  stops: Array<{
    stop_id: string
    stop_name: string
    stop_lat: number
    stop_lon: number
    match_score: number
  }>
}

export async function searchStops(
  query: string,
  options: {
    limit?: number
    signal?: AbortSignal
  } = {}
): Promise<StopSearchResult[]> {
  const normalizedQuery = query.trim()

  if (!normalizedQuery) {
    return []
  }

  const params = new URLSearchParams({
    q: normalizedQuery,
    limit: String(options.limit ?? 8),
  })

  const response = await apiFetch<StopSearchResponse>(`/stops/search?${params}`, {
    auth: true,
    signal: options.signal,
  })

  return response.stops.map((stop) => ({
    stopId: stop.stop_id,
    stopName: stop.stop_name,
    position: {
      lat: stop.stop_lat,
      lng: stop.stop_lon,
    },
    matchScore: stop.match_score,
  }))
}

