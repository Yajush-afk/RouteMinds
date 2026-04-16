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

const SEARCH_REQUEST_TIMEOUT_MS = 8_000

function withTimeout(signal: AbortSignal | undefined, timeoutMs: number) {
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

  const abortFromCaller = () => controller.abort()
  signal?.addEventListener("abort", abortFromCaller, { once: true })

  return {
    signal: controller.signal,
    cleanup: () => {
      window.clearTimeout(timeoutId)
      signal?.removeEventListener("abort", abortFromCaller)
    },
  }
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

  const request = withTimeout(options.signal, SEARCH_REQUEST_TIMEOUT_MS)

  try {
    const response = await apiFetch<StopSearchResponse>(`/stops/search?${params}`, {
      signal: request.signal,
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
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError" && !options.signal?.aborted) {
      throw new Error("Stop search timed out. Please try again.")
    }
    throw error
  } finally {
    request.cleanup()
  }
}
