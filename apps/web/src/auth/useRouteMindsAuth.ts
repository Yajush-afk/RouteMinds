import { useContext } from "react"

import { routeMindsAuthContext } from "@/auth/routeMindsAuthContext"

export function useRouteMindsAuth() {
  const context = useContext(routeMindsAuthContext)

  if (!context) {
    throw new Error(
      "useRouteMindsAuth must be used within SupabaseAuthProvider."
    )
  }

  return context
}
