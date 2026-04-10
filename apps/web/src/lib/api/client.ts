import { getApiBaseUrl } from "@/lib/api/config"

type AccessTokenFactory = () => Promise<string>

type ApiRequestOptions = RequestInit & {
  auth?: boolean
}

let accessTokenFactory: AccessTokenFactory | null = null

function resolveUrl(path: string) {
  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`
}

function extractErrorMessage(payload: unknown, fallback: string) {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload &&
    typeof payload.detail === "string" &&
    payload.detail.trim()
  ) {
    return payload.detail
  }

  return fallback
}

export function setApiAccessTokenFactory(factory: AccessTokenFactory | null) {
  accessTokenFactory = factory
}

export async function apiFetch<T>(
  path: string,
  { auth = false, headers, ...init }: ApiRequestOptions = {}
): Promise<T> {
  const requestHeaders = new Headers(headers)

  if (auth) {
    if (!accessTokenFactory) {
      throw new Error("Authenticated API access is not available.")
    }

    const token = await accessTokenFactory()
    requestHeaders.set("Authorization", `Bearer ${token}`)
  }

  if (init.body && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json")
  }

  const response = await fetch(resolveUrl(path), {
    ...init,
    headers: requestHeaders,
  })

  if (!response.ok) {
    let payload: unknown = null

    try {
      payload = await response.json()
    } catch {
      payload = null
    }

    throw new Error(
      extractErrorMessage(
        payload,
        `Request failed with status ${response.status}.`
      )
    )
  }

  return (await response.json()) as T
}
