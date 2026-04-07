import { buildApiUrl } from "@/api/config"

type RequestRouteMindsApiOptions = Omit<RequestInit, "headers"> & {
  headers?: HeadersInit
}

export async function requestRouteMindsApi(
  path: string,
  options: RequestRouteMindsApiOptions = {}
) {
  const { headers, ...requestOptions } = options

  return fetch(buildApiUrl(path), {
    ...requestOptions,
    headers: {
      Accept: "application/json",
      ...headers,
    },
  })
}
