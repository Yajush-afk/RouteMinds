import { apiFetch } from "@/lib/api/client"

import type {
  RouteSegmentPrediction,
  RouteStop,
} from "@/features/map/domain/types"

type RouteOptimizationResponse = {
  stops: Array<{
    stop_id: string
    stop_name: string
    stop_lat: number
    stop_lon: number
  }>
  segments: Array<{
    route_id: string
    from_stop_id: string
    to_stop_id: string
    scheduled_departure_unix: number | null
    stop_sequence: number
    normalized_stop_position: number
    distance_to_prev_stop_km: number
    scheduled_segment_minutes: number
    wait_minutes_before_boarding: number
    predicted_actual_segment_minutes: number
    predicted_segment_delay_minutes: number
  }>
  total_predicted_eta_minutes: number
}

const ROUTE_REQUEST_TIMEOUT_MS = 35_000

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

export type RouteOptimizationResult = {
  stops: RouteStop[]
  segments: RouteSegmentPrediction[]
  totalPredictedEtaMinutes: number
}

export async function optimizeRoute(
  originStopId: string,
  destinationStopId: string,
  queryTimestampUnix: number,
  options: {
    signal?: AbortSignal
  } = {}
): Promise<RouteOptimizationResult> {
  const request = withTimeout(options.signal, ROUTE_REQUEST_TIMEOUT_MS)

  try {
    const response = await apiFetch<RouteOptimizationResponse>("/routes/optimize", {
      auth: true,
      method: "POST",
      signal: request.signal,
      body: JSON.stringify({
        origin_stop_id: originStopId,
        destination_stop_id: destinationStopId,
        query_timestamp_unix: queryTimestampUnix,
      }),
    })

    return {
      stops: response.stops.map((stop) => ({
        stopId: stop.stop_id,
        stopName: stop.stop_name,
        position: {
          lat: stop.stop_lat,
          lng: stop.stop_lon,
        },
      })),
      segments: response.segments.map((segment) => ({
        routeId: segment.route_id,
        fromStopId: segment.from_stop_id,
        toStopId: segment.to_stop_id,
        scheduledDepartureUnix: segment.scheduled_departure_unix,
        stopSequence: segment.stop_sequence,
        normalizedStopPosition: segment.normalized_stop_position,
        distanceToPrevStopKm: segment.distance_to_prev_stop_km,
        scheduledSegmentMinutes: segment.scheduled_segment_minutes,
        waitMinutesBeforeBoarding: segment.wait_minutes_before_boarding,
        predictedActualSegmentMinutes: segment.predicted_actual_segment_minutes,
        predictedSegmentDelayMinutes: segment.predicted_segment_delay_minutes,
      })),
      totalPredictedEtaMinutes: response.total_predicted_eta_minutes,
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError" && !options.signal?.aborted) {
      throw new Error("Route optimization timed out. Try selecting a nearby alternative stop.")
    }
    throw error
  } finally {
    request.cleanup()
  }
}
