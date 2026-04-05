import { useEffect, useState } from "react"

import { useRouteMindsAuth } from "@/auth/Auth0ProviderWithNavigate"
import { fetchAuthSession, type AuthSessionResponse } from "@/lib/api/auth"

type ApiProbeState =
  | { kind: "idle" | "loading" }
  | { kind: "success"; session: AuthSessionResponse }
  | { kind: "error"; message: string }

export default function AuthenticatedApiStatus() {
  const { isAuthenticated, isLoading } = useRouteMindsAuth()
  const [probeState, setProbeState] = useState<ApiProbeState>({ kind: "idle" })

  useEffect(() => {
    if (isLoading || !isAuthenticated) {
      setProbeState({ kind: "idle" })
      return
    }

    let isCancelled = false

    async function verifySession() {
      setProbeState({ kind: "loading" })

      try {
        const session = await fetchAuthSession()

        if (!isCancelled) {
          setProbeState({ kind: "success", session })
        }
      } catch (error) {
        if (!isCancelled) {
          setProbeState({
            kind: "error",
            message:
              error instanceof Error
                ? error.message
                : "Protected API verification failed.",
          })
        }
      }
    }

    void verifySession()

    return () => {
      isCancelled = true
    }
  }, [isAuthenticated, isLoading])

  if (!isAuthenticated || probeState.kind === "idle") {
    return null
  }

  return (
    <div className="pointer-events-none absolute top-4 right-4 z-1000 max-w-sm rounded-2xl border border-black/5 bg-white/92 px-4 py-3 text-xs text-slate-700 shadow-lg backdrop-blur-md">
      {probeState.kind === "loading" ? <p>Verifying API session...</p> : null}
      {probeState.kind === "success" ? (
        <div className="space-y-1">
          <p className="font-semibold text-slate-900">API auth verified</p>
          <p className="truncate">Subject: {probeState.session.subject}</p>
        </div>
      ) : null}
      {probeState.kind === "error" ? (
        <div className="space-y-1 text-red-700">
          <p className="font-semibold">Protected API failed</p>
          <p>{probeState.message}</p>
        </div>
      ) : null}
    </div>
  )
}
