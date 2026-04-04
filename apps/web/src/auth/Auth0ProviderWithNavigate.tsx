import auth0 from "auth0-js"
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react"
import { useNavigate } from "react-router-dom"

import type { AuthResult, Auth0Error } from "auth0-js"

import { getAuth0Config, getAuth0ConfigError } from "@/auth/auth0-config"
import {
  parseIdentifier,
  type ParsedIdentifier,
} from "@/auth/identifier"

type Props = {
  children: ReactNode
}

type AuthUser = {
  email?: string
  name?: string
  picture?: string
  sub?: string
}

type PasswordlessStartResult = {
  channel: ParsedIdentifier["kind"]
  identifier: string
}

type RouteMindsAuthContextValue = {
  isConfigured: boolean
  configError: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: Error | null
  user: AuthUser | null
  getAccessToken: () => Promise<string>
  startPasswordless: (
    identifier: string,
    returnTo: string
  ) => Promise<PasswordlessStartResult>
  verifyPasswordless: (
    identifier: string,
    code: string,
    returnTo: string
  ) => Promise<void>
  loginWithGoogle: (returnTo: string) => Promise<void>
  logout: () => void
}

type StoredSession = {
  accessToken: string
  expiresAt: number
  idToken?: string | null
  scope?: string | null
  tokenType?: string | null
  user: AuthUser | null
}

const AUTH_SESSION_STORAGE_KEY = "routeminds.auth.session"

const RouteMindsAuthContext = createContext<RouteMindsAuthContextValue | null>(
  null
)

function toAuthError(error: Auth0Error | Error | null | undefined) {
  if (!error) {
    return null
  }

  if (error instanceof Error) {
    return error
  }

  return new Error(
    error.description ||
      error.errorDescription ||
      error.message ||
      error.error ||
      "Authentication failed."
  )
}

function toStoredSession(result: AuthResult): StoredSession | null {
  if (!result.accessToken || !result.expiresIn) {
    return null
  }

  return {
    accessToken: result.accessToken,
    expiresAt: Date.now() + result.expiresIn * 1000,
    idToken: result.idToken ?? null,
    scope: result.scope ?? null,
    tokenType: result.tokenType ?? null,
    user: result.idTokenPayload
      ? {
          email: result.idTokenPayload.email,
          name: result.idTokenPayload.name,
          picture: result.idTokenPayload.picture,
          sub: result.idTokenPayload.sub,
        }
      : null,
  }
}

function readStoredSession() {
  const raw = sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY)

  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw) as StoredSession
    if (parsed.expiresAt <= Date.now() || !parsed.accessToken) {
      sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY)
      return null
    }

    return parsed
  } catch {
    sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY)
    return null
  }
}

function storeSession(session: StoredSession | null) {
  if (!session) {
    sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY)
    return
  }

  sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session))
}

function getReturnTo(appState: unknown) {
  if (
    appState &&
    typeof appState === "object" &&
    "returnTo" in appState &&
    typeof appState.returnTo === "string" &&
    appState.returnTo
  ) {
    return appState.returnTo
  }

  return "/"
}

function createUnavailableAuthValue(
  message: string
): RouteMindsAuthContextValue {
  const error = new Error(message)

  async function rejectVoid() {
    throw error
  }

  async function rejectString(): Promise<string> {
    throw error
  }

  async function rejectPasswordlessStart(): Promise<PasswordlessStartResult> {
    throw error
  }

  return {
    isConfigured: false,
    configError: message,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    user: null,
    getAccessToken: rejectString,
    startPasswordless: rejectPasswordlessStart,
    verifyPasswordless: rejectVoid,
    loginWithGoogle: rejectVoid,
    logout() {},
  }
}

export default function Auth0ProviderWithNavigate({ children }: Props) {
  const navigate = useNavigate()
  const config = getAuth0Config()
  const configError = getAuth0ConfigError()
  const [error, setError] = useState<Error | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [session, setSession] = useState<StoredSession | null>(null)

  const webAuth = useMemo(() => {
    if (!config) {
      return null
    }

    return new auth0.WebAuth({
      domain: config.domain,
      clientID: config.clientId,
      redirectUri: config.redirectUri,
      responseType: "token id_token",
      scope: config.scope,
      ...(config.audience ? { audience: config.audience } : {}),
    })
  }, [config])

  const resetError = useCallback(() => {
    setError(null)
  }, [])

  const commitSession = useCallback((nextSession: StoredSession | null) => {
    setSession(nextSession)
    storeSession(nextSession)
  }, [])

  useEffect(() => {
    if (!webAuth) {
      setIsLoading(false)
      return
    }

    const hash = window.location.hash
    const hasAuthResponse =
      hash.includes("access_token") ||
      hash.includes("id_token") ||
      hash.includes("error=")

    if (hasAuthResponse) {
      webAuth.parseHash({ hash }, (parseError, result) => {
        const nextError = toAuthError(parseError)

        if (nextError) {
          resetError()
          commitSession(null)
          setError(nextError)
          setIsLoading(false)
          window.history.replaceState(
            {},
            document.title,
            `${window.location.pathname}${window.location.search}`
          )
          return
        }

        const nextSession = result ? toStoredSession(result) : null

        if (!nextSession) {
          commitSession(null)
          setError(new Error("Authentication response did not contain a valid session."))
          setIsLoading(false)
          return
        }

        resetError()
        commitSession(nextSession)
        setIsLoading(false)
        navigate(getReturnTo(result?.appState), { replace: true })
      })
      return
    }

    const storedSession = readStoredSession()
    commitSession(storedSession)
    setIsLoading(false)
  }, [commitSession, navigate, resetError, webAuth])

  const startPasswordless = useCallback<RouteMindsAuthContextValue["startPasswordless"]>(
    async (rawIdentifier) => {
      if (!webAuth || !config) {
        throw new Error(configError ?? "Auth0 configuration is unavailable.")
      }

      resetError()

      const identifier = parseIdentifier(rawIdentifier)

      await new Promise<void>((resolve, reject) => {
        webAuth.passwordlessStart(
          {
            connection:
              identifier.kind === "email"
                ? config.emailConnection
                : config.smsConnection,
            send: "code",
            ...(identifier.kind === "email"
              ? { email: identifier.value }
              : { phoneNumber: identifier.value }),
            authParams: {
              scope: config.scope,
              ...(config.audience ? { audience: config.audience } : {}),
            },
          },
          (startError) => {
            const nextError = toAuthError(startError)
            if (nextError) {
              reject(nextError)
              return
            }

            resolve()
          }
        )
      })

      return {
        channel: identifier.kind,
        identifier: identifier.value,
      }
    },
    [config, configError, resetError, webAuth]
  )

  const verifyPasswordless = useCallback<RouteMindsAuthContextValue["verifyPasswordless"]>(
    async (rawIdentifier, code, returnTo) => {
      if (!webAuth || !config) {
        throw new Error(configError ?? "Auth0 configuration is unavailable.")
      }

      resetError()
      const identifier = parseIdentifier(rawIdentifier)

      await new Promise<void>((resolve, reject) => {
        webAuth.passwordlessLogin(
          {
            connection:
              identifier.kind === "email"
                ? config.emailConnection
                : config.smsConnection,
            verificationCode: code,
            ...(identifier.kind === "email"
              ? { email: identifier.value }
              : { phoneNumber: identifier.value }),
            appState: { returnTo },
            onRedirecting(done) {
              done()
              resolve()
            },
          },
          (loginError) => {
            const nextError = toAuthError(loginError)
            if (nextError) {
              reject(nextError)
            }
          }
        )
      })
    },
    [config, configError, resetError, webAuth]
  )

  const loginWithGoogle = useCallback<RouteMindsAuthContextValue["loginWithGoogle"]>(
    async (returnTo) => {
      if (!webAuth || !config) {
        throw new Error(configError ?? "Auth0 configuration is unavailable.")
      }

      resetError()
      webAuth.authorize({
        ...(config.googleConnection
          ? { connection: config.googleConnection }
          : {}),
        appState: { returnTo },
      })
    },
    [config, configError, resetError, webAuth]
  )

  const logout = useCallback(() => {
    commitSession(null)
    resetError()

    if (!webAuth || !config) {
      navigate("/", { replace: true })
      return
    }

    webAuth.logout({
      clientID: config.clientId,
      returnTo: window.location.origin,
    })
  }, [commitSession, config, navigate, resetError, webAuth])

  const getAccessToken = useCallback<RouteMindsAuthContextValue["getAccessToken"]>(
    async () => {
      const currentSession = readStoredSession()

      if (!currentSession) {
        commitSession(null)
        throw new Error("No authenticated session is available.")
      }

      commitSession(currentSession)
      return currentSession.accessToken
    },
    [commitSession]
  )

  if (!config) {
    return (
      <RouteMindsAuthContext.Provider
        value={createUnavailableAuthValue(
          configError ?? "Auth0 configuration is unavailable."
        )}
      >
        {children}
      </RouteMindsAuthContext.Provider>
    )
  }

  return (
    <RouteMindsAuthContext.Provider
      value={{
        isConfigured: true,
        configError: null,
        isAuthenticated: !!session,
        isLoading,
        error,
        user: session?.user ?? null,
        getAccessToken,
        startPasswordless,
        verifyPasswordless,
        loginWithGoogle,
        logout,
      }}
    >
      {children}
    </RouteMindsAuthContext.Provider>
  )
}

export function useRouteMindsAuth() {
  const context = useContext(RouteMindsAuthContext)

  if (!context) {
    throw new Error(
      "useRouteMindsAuth must be used within Auth0ProviderWithNavigate."
    )
  }

  return context
}
