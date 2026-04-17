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

  async function readErrorPayload(response: Response) {
    try {
      return await response.json()
    } catch {
      return null
    }
  }

  let response = await performRequest()
  let payload: unknown = null
  let hasRetriedAfterRefresh = false

  while (!response.ok) {
    payload = await readErrorPayload(response)

    if (auth && response.status === 401 && !hasRetriedAfterRefresh) {
      hasRetriedAfterRefresh = true
      response = await performRequest({ forceRefresh: true })
      continue
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
