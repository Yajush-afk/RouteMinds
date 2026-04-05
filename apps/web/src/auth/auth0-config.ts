export type Auth0Config = {
  audience: string
  domain: string
  clientId: string
  emailConnection: string
  googleConnection?: string
  redirectUri: string
  scope: string
  smsConnection: string
}

function readRequiredEnv(
  name: "VITE_AUTH0_AUDIENCE" | "VITE_AUTH0_CLIENT_ID" | "VITE_AUTH0_DOMAIN"
) {
  return import.meta.env[name]?.trim() || ""
}

export function getAuth0ConfigError() {
  const missing = [
    !readRequiredEnv("VITE_AUTH0_DOMAIN") ? "VITE_AUTH0_DOMAIN" : null,
    !readRequiredEnv("VITE_AUTH0_CLIENT_ID") ? "VITE_AUTH0_CLIENT_ID" : null,
    !readRequiredEnv("VITE_AUTH0_AUDIENCE") ? "VITE_AUTH0_AUDIENCE" : null,
  ].filter(Boolean)

  if (missing.length === 0) {
    return null
  }

  return `Missing ${missing.join(" and ")}. Add them to apps/web/.env.local before using Auth0.`
}

export function getAuth0Config(): Auth0Config | null {
  const error = getAuth0ConfigError()

  if (error) {
    return null
  }

  return {
    audience: readRequiredEnv("VITE_AUTH0_AUDIENCE"),
    domain: readRequiredEnv("VITE_AUTH0_DOMAIN"),
    clientId: readRequiredEnv("VITE_AUTH0_CLIENT_ID"),
    emailConnection:
      import.meta.env.VITE_AUTH0_EMAIL_CONNECTION?.trim() || "email",
    googleConnection:
      import.meta.env.VITE_AUTH0_GOOGLE_CONNECTION?.trim() || undefined,
    redirectUri: `${window.location.origin}/auth`,
    scope: import.meta.env.VITE_AUTH0_SCOPE?.trim() || "openid profile email",
    smsConnection: import.meta.env.VITE_AUTH0_SMS_CONNECTION?.trim() || "sms",
  }
}
