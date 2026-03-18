import type { LngLat, PlaceSuggestion } from "@/features/map/domain/types"

const NOMINATIM_REVERSE_ENDPOINT = "https://nominatim.openstreetmap.org/reverse"
const NOMINATIM_SEARCH_ENDPOINT = "https://nominatim.openstreetmap.org/search"

type SearchPlacesOptions = {
  signal?: AbortSignal
  language?: string
  countryCode?: string
  limit?: number
}

type ReverseGeocodeOptions = {
  signal?: AbortSignal
  language?: string
}

type NominatimSearchResponseItem = {
  place_id: number
  display_name: string
  lat: string
  lon: string
}

type NominatimReverseResponse = {
  display_name?: string
  error?: string
}

function getContactEmail() {
  return import.meta.env.VITE_NOMINATIM_EMAIL?.trim()
}

export async function searchPlaces(
  query: string,
  options: SearchPlacesOptions = {}
): Promise<PlaceSuggestion[]> {
  const normalizedQuery = query.trim()

  if (!normalizedQuery) {
    return []
  }

  const params = new URLSearchParams({
    q: normalizedQuery,
    format: "jsonv2",
    addressdetails: "1",
    limit: String(options.limit ?? 5),
    countrycodes: options.countryCode ?? "in",
  })

  const contactEmail = getContactEmail()
  if (contactEmail) {
    params.set("email", contactEmail)
  }

  if (options.language) {
    params.set("accept-language", options.language)
  }

  const response = await fetch(`${NOMINATIM_SEARCH_ENDPOINT}?${params}`, {
    signal: options.signal,
    headers: {
      Accept: "application/json",
    },
  })

  if (!response.ok) {
    throw new Error("Unable to search places.")
  }

  const payload = (await response.json()) as NominatimSearchResponseItem[]

  return payload.map((item) => ({
    id: String(item.place_id),
    label: item.display_name,
    position: {
      lat: Number(item.lat),
      lng: Number(item.lon),
    },
  }))
}

export async function reverseGeocode(
  position: LngLat,
  options: ReverseGeocodeOptions = {}
): Promise<string | null> {
  const params = new URLSearchParams({
    format: "jsonv2",
    lat: String(position.lat),
    lon: String(position.lng),
    addressdetails: "1",
    zoom: "18",
  })

  const contactEmail = getContactEmail()
  if (contactEmail) {
    params.set("email", contactEmail)
  }

  if (options.language) {
    params.set("accept-language", options.language)
  }

  const response = await fetch(`${NOMINATIM_REVERSE_ENDPOINT}?${params}`, {
    signal: options.signal,
    headers: {
      Accept: "application/json",
    },
  })

  if (!response.ok) {
    throw new Error("Unable to reverse geocode location.")
  }

  const payload = (await response.json()) as NominatimReverseResponse

  if (payload.error) {
    throw new Error(payload.error)
  }

  return payload.display_name ?? null
}
