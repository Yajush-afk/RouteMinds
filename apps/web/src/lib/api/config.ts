function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "")
}

export function getApiBaseUrl() {
  const configuredValue = import.meta.env.VITE_API_BASE_URL?.trim()

  if (configuredValue) {
    return trimTrailingSlash(configuredValue)
  }

  return "http://127.0.0.1:8000"
}
