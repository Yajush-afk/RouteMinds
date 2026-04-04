import { Navigate, Outlet, useLocation } from "react-router-dom"

import { useRouteMindsAuth } from "@/auth/Auth0ProviderWithNavigate"

function buildAuthPath(returnTo: string) {
  const searchParams = new URLSearchParams({ returnTo })
  return `/auth?${searchParams.toString()}`
}

function AuthStatusScreen({
  title,
  message,
}: {
  title: string
  message: string
}) {
  return (
    <main className="grid min-h-screen place-items-center bg-background px-6">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold text-foreground">{title}</h1>
        <p className="mt-3 text-sm text-muted-foreground">{message}</p>
      </div>
    </main>
  )
}

export default function ProtectedRoute() {
  const { configError, error, isAuthenticated, isConfigured, isLoading } =
    useRouteMindsAuth()
  const location = useLocation()

  if (!isConfigured) {
    return (
      <AuthStatusScreen
        title="Authentication is not configured"
        message={configError ?? "Auth0 configuration is unavailable."}
      />
    )
  }

  if (isLoading) {
    return (
      <AuthStatusScreen
        title="Checking your session"
        message="RouteMinds is verifying your login before opening the map."
      />
    )
  }

  if (error) {
    return (
      <AuthStatusScreen
        title="Authentication is unavailable"
        message={error.message}
      />
    )
  }

  if (!isAuthenticated) {
    const returnTo = `${location.pathname}${location.search}${location.hash}`
    return <Navigate replace to={buildAuthPath(returnTo)} />
  }

  return <Outlet />
}
