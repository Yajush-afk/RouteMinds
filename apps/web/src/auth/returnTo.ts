export function normalizeReturnToPath(rawValue: string | null | undefined) {
  const value = rawValue?.trim() || ""

  if (!value.startsWith("/") || value.startsWith("//")) {
    return "/map"
  }

  return value
}

export function buildAuthPath(returnTo: string) {
  const searchParams = new URLSearchParams({
    returnTo: normalizeReturnToPath(returnTo),
  })
  return `/auth?${searchParams.toString()}`
}
