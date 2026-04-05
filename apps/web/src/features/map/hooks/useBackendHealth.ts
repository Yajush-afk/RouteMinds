import { useEffect, useState } from "react"

import { requestRouteMindsApi } from "@/api/client"
import { getApiBaseUrl } from "@/api/config"

const HEALTH_CHECK_INTERVAL_MS = 30000

type HealthResponse = {
  status?: string
}

export type BackendHealthState = {
  apiBaseUrl: string
  description: string
  status: "checking" | "online" | "offline"
}

const initialState: BackendHealthState = {
  apiBaseUrl: getApiBaseUrl(),
  description: "Checking the RouteMinds API connection.",
  status: "checking",
}

export function useBackendHealth() {
  const [backendHealth, setBackendHealth] =
    useState<BackendHealthState>(initialState)

  useEffect(() => {
    let isDisposed = false
    let isChecking = false

    const apiBaseUrl = getApiBaseUrl()

    const checkBackendHealth = async () => {
      if (isChecking) {
        return
      }

      isChecking = true

      try {
        const response = await requestRouteMindsApi("/health")
        const payload = (await response.json()) as HealthResponse

        if (isDisposed) {
          return
        }

        if (!response.ok || payload.status !== "healthy") {
          setBackendHealth({
            apiBaseUrl,
            description:
              "The RouteMinds API responded unexpectedly. Check the backend server and API base URL.",
            status: "offline",
          })
          return
        }

        setBackendHealth({
          apiBaseUrl,
          description: "Connected to the RouteMinds backend.",
          status: "online",
        })
      } catch {
        if (isDisposed) {
          return
        }

        setBackendHealth({
          apiBaseUrl,
          description:
            "The RouteMinds API is unavailable. Start the backend or update VITE_API_BASE_URL.",
          status: "offline",
        })
      } finally {
        isChecking = false
      }
    }

    void checkBackendHealth()

    const intervalId = window.setInterval(() => {
      void checkBackendHealth()
    }, HEALTH_CHECK_INTERVAL_MS)

    return () => {
      isDisposed = true
      window.clearInterval(intervalId)
    }
  }, [])

  return backendHealth
}

export default useBackendHealth
