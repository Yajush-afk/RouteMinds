export type Auth0Config = {
  domain: string
  clientId: string
  audience?: string
  emailConnection: string
  googleConnection?: string
  redirectUri: string
  scope: string
  smsConnection: string
}

function readOptionalEnv(name: "VITE_AUTH0_DOMAIN" | "VITE_AUTH0_CLIENT_ID") {
  return import.meta.env[name]?.trim() || ""
}

export function getAuth0ConfigError() {
  const missing = [
    !readOptionalEnv("VITE_AUTH0_DOMAIN") ? "VITE_AUTH0_DOMAIN" : null,
    !readOptionalEnv("VITE_AUTH0_CLIENT_ID") ? "VITE_AUTH0_CLIENT_ID" : null,
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
    domain: readOptionalEnv("VITE_AUTH0_DOMAIN"),
    clientId: readOptionalEnv("VITE_AUTH0_CLIENT_ID"),
    audience: import.meta.env.VITE_AUTH0_AUDIENCE?.trim() || undefined,
    emailConnection: import.meta.env.VITE_AUTH0_EMAIL_CONNECTION?.trim() || "email",
    googleConnection: import.meta.env.VITE_AUTH0_GOOGLE_CONNECTION?.trim() || undefined,
    redirectUri: window.location.origin,
    scope: import.meta.env.VITE_AUTH0_SCOPE?.trim() || "openid profile email",
    smsConnection: import.meta.env.VITE_AUTH0_SMS_CONNECTION?.trim() || "sms",
  }
}
