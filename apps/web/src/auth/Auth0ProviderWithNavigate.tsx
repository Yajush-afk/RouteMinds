import { Auth0Provider, type AppState, useAuth0 } from "@auth0/auth0-react"
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
} from "react"
import { useNavigate } from "react-router-dom"

import { getAuth0Config, getAuth0ConfigError } from "@/auth/auth0-config"
import { parseIdentifier } from "@/auth/identifier"
import { setApiAccessTokenFactory } from "@/lib/api/client"

type Props = {
  children: ReactNode
}

type AuthUser = {
  email?: string
  name?: string
  picture?: string
  sub?: string
}

type RouteMindsAuthContextValue = {
  isConfigured: boolean
  configError: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: Error | null
  user: AuthUser | null
  getAccessToken: () => Promise<string>
  startPasswordless: (identifier: string, returnTo: string) => Promise<void>
  loginWithGoogle: (returnTo: string) => Promise<void>
  logout: () => void
}

type AuthUserShape = {
  email?: string
  name?: string
  picture?: string
  sub?: string
}

type RouteMindsAppState = AppState & {
  returnTo?: string
}

const RouteMindsAuthContext = createContext<RouteMindsAuthContextValue | null>(
  null
)

function getReturnTo(appState?: RouteMindsAppState) {
  const returnTo = appState?.returnTo?.trim() || "/"
  return returnTo.startsWith("/") ? returnTo : "/"
}

function toAuthUser(user: AuthUserShape | undefined): AuthUser | null {
  if (!user) {
    return null
  }

  return {
    email: user.email,
    name: user.name,
    picture: user.picture,
    sub: user.sub,
  }
}

function toAuthError(error: unknown) {
  if (!error) {
    return null
  }

  if (error instanceof Error) {
    return error
  }

  return new Error("Authentication failed.")
}

function createUnavailableAuthValue(
  message: string
): RouteMindsAuthContextValue {
  const error = new Error(message)

  async function rejectVoid(): Promise<void> {
    throw error
  }

  async function rejectString(): Promise<string> {
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
    startPasswordless: rejectVoid,
    loginWithGoogle: rejectVoid,
    logout() {},
  }
}

function AuthStateBridge({
  children,
  config,
}: Props & { config: NonNullable<ReturnType<typeof getAuth0Config>> }) {
  const {
    error,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout: auth0Logout,
    user,
  } = useAuth0()

  const getAccessToken = useCallback(async () => {
    return getAccessTokenSilently({
      authorizationParams: {
        audience: config.audience,
        scope: config.scope,
      },
    })
  }, [config.audience, config.scope, getAccessTokenSilently])

  useEffect(() => {
    setApiAccessTokenFactory(() =>
      getAccessTokenSilently({
        authorizationParams: {
          audience: config.audience,
          scope: config.scope,
        },
      })
    )

    return () => {
      setApiAccessTokenFactory(null)
    }
  }, [config.audience, config.scope, getAccessTokenSilently])

  const startPasswordless = useCallback<
    RouteMindsAuthContextValue["startPasswordless"]
  >(
    async (rawIdentifier, returnTo) => {
      const identifier = parseIdentifier(rawIdentifier)

      await loginWithRedirect({
        appState: { returnTo },
        authorizationParams: {
          audience: config.audience,
          connection:
            identifier.kind === "email"
              ? config.emailConnection
              : config.smsConnection,
          login_hint: identifier.value,
          redirect_uri: config.redirectUri,
          scope: config.scope,
        },
      })
    },
    [
      config.audience,
      config.emailConnection,
      config.redirectUri,
      config.scope,
      config.smsConnection,
      loginWithRedirect,
    ]
  )

  const loginWithGoogle = useCallback<
    RouteMindsAuthContextValue["loginWithGoogle"]
  >(
    async (returnTo) => {
      await loginWithRedirect({
        appState: { returnTo },
        authorizationParams: {
          audience: config.audience,
          ...(config.googleConnection
            ? { connection: config.googleConnection }
            : {}),
          redirect_uri: config.redirectUri,
          scope: config.scope,
        },
      })
    },
    [
      config.audience,
      config.googleConnection,
      config.redirectUri,
      config.scope,
      loginWithRedirect,
    ]
  )

  const logout = useCallback(() => {
    setApiAccessTokenFactory(null)
    auth0Logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    })
  }, [auth0Logout])

  const value = useMemo<RouteMindsAuthContextValue>(
    () => ({
      isConfigured: true,
      configError: null,
      isAuthenticated,
      isLoading,
      error: toAuthError(error),
      user: toAuthUser(user as AuthUserShape | undefined),
      getAccessToken,
      startPasswordless,
      loginWithGoogle,
      logout,
    }),
    [
      error,
      getAccessToken,
      isAuthenticated,
      isLoading,
      loginWithGoogle,
      logout,
      startPasswordless,
      user,
    ]
  )

  return (
    <RouteMindsAuthContext.Provider value={value}>
      {children}
    </RouteMindsAuthContext.Provider>
  )
}

export default function Auth0ProviderWithNavigate({ children }: Props) {
  const navigate = useNavigate()
  const config = getAuth0Config()
  const configError = getAuth0ConfigError()

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
    <Auth0Provider
      domain={config.domain}
      clientId={config.clientId}
      authorizationParams={{
        audience: config.audience,
        redirect_uri: config.redirectUri,
        scope: config.scope,
      }}
      onRedirectCallback={(appState) => {
        navigate(getReturnTo(appState as RouteMindsAppState), {
          replace: true,
        })
      }}
    >
      <AuthStateBridge config={config}>{children}</AuthStateBridge>
    </Auth0Provider>
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
