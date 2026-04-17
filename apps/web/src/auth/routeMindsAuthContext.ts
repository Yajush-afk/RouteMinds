import { createContext } from "react"

type AuthUser = {
  email?: string
  name?: string
  picture?: string
  sub?: string
}

export type RouteMindsAuthContextValue = {
  isConfigured: boolean
  configError: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: Error | null
  user: AuthUser | null
  getAccessToken: () => Promise<string>
  startPasswordless: (identifier: string, returnTo: string) => Promise<void>
  loginWithGoogle: (returnTo: string) => Promise<void>
  verifyOneTimePassword: (token: string) => Promise<void>
  pendingIdentifier: string | null
  pendingIdentifierKind: "email" | null
  clearPendingIdentifier: () => void
  logout: () => Promise<void>
}

export const routeMindsAuthContext =
  createContext<RouteMindsAuthContextValue | null>(null)
