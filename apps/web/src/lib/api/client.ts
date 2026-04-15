import { getApiBaseUrl } from "@/lib/api/config"

type AccessTokenFactory = (options?: {
  forceRefresh?: boolean
}) => Promise<string>

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
  async function performRequest(options?: { forceRefresh?: boolean }) {
    const requestHeaders = new Headers(headers)

    if (auth) {
      if (!accessTokenFactory) {
        throw new Error("Authenticated API access is not available.")
      }

      const token = await accessTokenFactory(options)
      requestHeaders.set("Authorization", `Bearer ${token}`)
    }

    if (init.body && !requestHeaders.has("Content-Type")) {
      requestHeaders.set("Content-Type", "application/json")
    }

    return fetch(resolveUrl(path), {
      ...init,
      headers: requestHeaders,
    })
  }

  let response = await performRequest()
  let payload: unknown = null

  if (!response.ok) {
    try {
      payload = await response.json()
    } catch {
      payload = null
    }

    const message = extractErrorMessage(
      payload,
      `Request failed with status ${response.status}.`
    )

    if (
      auth &&
      response.status === 401 &&
      message === "Invalid or expired Supabase access token."
    ) {
      response = await performRequest({ forceRefresh: true })

      if (!response.ok) {
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
    } else {
      throw new Error(message)
    }
  }

  return (await response.json()) as T
}
