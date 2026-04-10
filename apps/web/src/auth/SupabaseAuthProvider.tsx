import type { Session, User } from "@supabase/supabase-js"
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react"

import { type ParsedIdentifier, parseIdentifier } from "@/auth/identifier"
import { normalizeReturnToPath } from "@/auth/returnTo"
import {
  routeMindsAuthContext,
  type RouteMindsAuthContextValue,
} from "@/auth/routeMindsAuthContext"
import { setApiAccessTokenFactory } from "@/lib/api/client"
import { createClient as createSupabaseClient } from "@/lib/supabase/client"

type Props = {
  children: ReactNode
}

type AuthUser = {
  email?: string
  name?: string
  picture?: string
  sub?: string
}

const PENDING_IDENTIFIER_STORAGE_KEY = "routeminds.pending-auth-identifier"
const PENDING_RETURN_TO_STORAGE_KEY = "routeminds.pending-auth-return-to"

let supabaseClient: ReturnType<typeof createSupabaseClient> | null = null

function toAuthUser(user: User | null): AuthUser | null {
  if (!user) {
    return null
  }

  return {
    email: user.email ?? undefined,
    name:
      typeof user.user_metadata?.name === "string"
        ? user.user_metadata.name
        : typeof user.user_metadata?.full_name === "string"
          ? user.user_metadata.full_name
          : undefined,
    picture:
      typeof user.user_metadata?.avatar_url === "string"
        ? user.user_metadata.avatar_url
        : typeof user.user_metadata?.picture === "string"
          ? user.user_metadata.picture
          : undefined,
    sub: user.id,
  }
}

function readPendingIdentifier() {
  if (typeof window === "undefined") {
    return null
  }

  return (
    window.sessionStorage.getItem(PENDING_IDENTIFIER_STORAGE_KEY)?.trim() ||
    null
  )
}

function writePendingIdentifier(identifier: ParsedIdentifier | null) {
  if (typeof window === "undefined") {
    return
  }

  if (!identifier) {
    window.sessionStorage.removeItem(PENDING_IDENTIFIER_STORAGE_KEY)
    return
  }

  window.sessionStorage.setItem(
    PENDING_IDENTIFIER_STORAGE_KEY,
    JSON.stringify(identifier)
  )
}

function readPendingReturnTo() {
  if (typeof window === "undefined") {
    return "/map"
  }

  return normalizeReturnToPath(
    window.sessionStorage.getItem(PENDING_RETURN_TO_STORAGE_KEY)
  )
}

function writePendingReturnTo(returnTo: string | null) {
  if (typeof window === "undefined") {
    return
  }

  if (!returnTo) {
    window.sessionStorage.removeItem(PENDING_RETURN_TO_STORAGE_KEY)
    return
  }

  window.sessionStorage.setItem(
    PENDING_RETURN_TO_STORAGE_KEY,
    normalizeReturnToPath(returnTo)
  )
}

function getPendingIdentifierState() {
  const rawValue = readPendingIdentifier()

  if (!rawValue) {
    return {
      pendingIdentifier: null,
      pendingIdentifierKind: null,
    } as const
  }

  try {
    const parsed = JSON.parse(rawValue) as ParsedIdentifier

    if (
      parsed &&
      (parsed.kind === "email" || parsed.kind === "sms") &&
      typeof parsed.value === "string" &&
      parsed.value.trim()
    ) {
      return {
        pendingIdentifier: parsed.value,
        pendingIdentifierKind: parsed.kind,
      } as const
    }
  } catch {
    writePendingIdentifier(null)
  }

  return {
    pendingIdentifier: null,
    pendingIdentifierKind: null,
  } as const
}

function getSupabaseConfigError() {
  try {
    getSupabaseClient()
    return null
  } catch (error) {
    return error instanceof Error
      ? error.message
      : "Supabase configuration is unavailable."
  }
}

function getSupabaseClient() {
  if (!supabaseClient) {
    supabaseClient = createSupabaseClient()
  }

  return supabaseClient
}

type SessionResult = {
  data: {
    session: Session | null
  }
  error: Error | null
}

export default function SupabaseAuthProvider({ children }: Props) {
  const configError = getSupabaseConfigError()
  const [
    { pendingIdentifier, pendingIdentifierKind },
    setPendingIdentifierState,
  ] = useState(() => getPendingIdentifierState())
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(() => !configError)
  const [error, setError] = useState<Error | null>(null)

  const clearPendingIdentifier = useCallback(() => {
    writePendingIdentifier(null)
    writePendingReturnTo(null)
    setPendingIdentifierState({
      pendingIdentifier: null,
      pendingIdentifierKind: null,
    })
  }, [])

  useEffect(() => {
    if (configError) {
      setApiAccessTokenFactory(null)
      return
    }

    const supabase = getSupabaseClient()
    let isActive = true

    void supabase.auth
      .getSession()
      .then(({ data, error: sessionError }: SessionResult) => {
        if (!isActive) {
          return
        }

        if (sessionError) {
          setError(sessionError)
        } else {
          const accessToken = data.session?.access_token

          setError(null)
          setSession(data.session)
          setApiAccessTokenFactory(accessToken ? async () => accessToken : null)
        }

        setIsLoading(false)
      })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      (_event: string, nextSession: Session | null) => {
        if (!isActive) {
          return
        }

        setSession(nextSession)
        setIsLoading(false)
        setError(null)

        if (nextSession?.access_token) {
          setApiAccessTokenFactory(async () => nextSession.access_token)
          clearPendingIdentifier()
        } else {
          setApiAccessTokenFactory(null)
        }
      }
    )

    return () => {
      isActive = false
      subscription.unsubscribe()
      setApiAccessTokenFactory(null)
    }
  }, [clearPendingIdentifier, configError])

  const getAccessToken = useCallback(async () => {
    const supabase = getSupabaseClient()
    const { data, error } = await supabase.auth.getSession()

    if (error) {
      throw error
    }

    const accessToken = data.session?.access_token?.trim()

    if (!accessToken) {
      throw new Error("Authenticated API access is not available.")
    }

    return accessToken
  }, [])

  const startPasswordless = useCallback<
    RouteMindsAuthContextValue["startPasswordless"]
  >(async (rawIdentifier, returnTo) => {
    const supabase = getSupabaseClient()
    const identifier = parseIdentifier(rawIdentifier)
    const normalizedReturnTo = normalizeReturnToPath(returnTo)

    setError(null)

    const { error } =
      identifier.kind === "email"
        ? await supabase.auth.signInWithOtp({
            email: identifier.value,
            options: {
              emailRedirectTo: `${window.location.origin}/auth?returnTo=${encodeURIComponent(normalizedReturnTo)}`,
              shouldCreateUser: true,
            },
          })
        : await supabase.auth.signInWithOtp({
            phone: identifier.value,
            options: {
              channel: "sms",
              shouldCreateUser: true,
            },
          })

    if (error) {
      setError(error)
      throw error
    }

    writePendingIdentifier(identifier)
    writePendingReturnTo(normalizedReturnTo)
    setPendingIdentifierState({
      pendingIdentifier: identifier.value,
      pendingIdentifierKind: identifier.kind,
    })
  }, [])

  const verifyOneTimePassword = useCallback<
    RouteMindsAuthContextValue["verifyOneTimePassword"]
  >(
    async (token) => {
      const supabase = getSupabaseClient()
      const identifierState = getPendingIdentifierState()

      if (
        !identifierState.pendingIdentifier ||
        !identifierState.pendingIdentifierKind
      ) {
        throw new Error(
          "Start sign-in first so we know where to verify the code."
        )
      }

      const normalizedToken = token.trim()

      if (normalizedToken.length !== 6) {
        throw new Error("Enter the 6-digit code we sent you.")
      }

      setError(null)

      const { error } =
        identifierState.pendingIdentifierKind === "email"
          ? await supabase.auth.verifyOtp({
              email: identifierState.pendingIdentifier,
              token: normalizedToken,
              type: "email",
              options: {
                redirectTo: `${window.location.origin}${readPendingReturnTo()}`,
              },
            })
          : await supabase.auth.verifyOtp({
              phone: identifierState.pendingIdentifier,
              token: normalizedToken,
              type: "sms",
              options: {
                redirectTo: `${window.location.origin}${readPendingReturnTo()}`,
              },
            })

      if (error) {
        setError(error)
        throw error
      }

      clearPendingIdentifier()
    },
    [clearPendingIdentifier]
  )

  const loginWithGoogle = useCallback<
    RouteMindsAuthContextValue["loginWithGoogle"]
  >(async (returnTo) => {
    const supabase = getSupabaseClient()
    const normalizedReturnTo = normalizeReturnToPath(returnTo)
    setError(null)
    writePendingReturnTo(normalizedReturnTo)

    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth?returnTo=${encodeURIComponent(normalizedReturnTo)}`,
      },
    })

    if (error) {
      writePendingReturnTo(null)
      setError(error)
      throw error
    }
  }, [])

  const logout = useCallback(() => {
    const supabase = getSupabaseClient()
    clearPendingIdentifier()
    setApiAccessTokenFactory(null)
    void supabase.auth.signOut()
  }, [clearPendingIdentifier])

  const value = useMemo<RouteMindsAuthContextValue>(
    () => ({
      isConfigured: !configError,
      configError,
      isAuthenticated: !!session?.user,
      isLoading,
      error,
      user: toAuthUser(session?.user ?? null),
      getAccessToken,
      startPasswordless,
      loginWithGoogle,
      verifyOneTimePassword,
      pendingIdentifier,
      pendingIdentifierKind,
      clearPendingIdentifier,
      logout,
    }),
    [
      clearPendingIdentifier,
      configError,
      error,
      getAccessToken,
      isLoading,
      loginWithGoogle,
      logout,
      pendingIdentifier,
      pendingIdentifierKind,
      session,
      startPasswordless,
      verifyOneTimePassword,
    ]
  )

  return (
    <routeMindsAuthContext.Provider value={value}>
      {children}
    </routeMindsAuthContext.Provider>
  )
}
