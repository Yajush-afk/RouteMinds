import type { LatLngTuple } from "leaflet"

const NOMINATIM_REVERSE_ENDPOINT = "https://nominatim.openstreetmap.org/reverse"
const NOMINATIM_SEARCH_ENDPOINT = "https://nominatim.openstreetmap.org/search"

type ReverseGeocodeOptions = {
  signal?: AbortSignal
  language?: string
}

type NominatimReverseResponse = {
  display_name?: string
  error?: string
}

type NominatimSearchResponseItem = {
  place_id: number
  display_name: string
  lat: string
  lon: string
}

type SearchPlacesOptions = {
  signal?: AbortSignal
  language?: string
  countryCode?: string
  limit?: number
}

export type SearchPlaceResult = {
  placeId: number
  displayName: string
  lat: number
  lon: number
}

export async function searchPlaces(
  query: string,
  options: SearchPlacesOptions = {}
): Promise<SearchPlaceResult[]> {
  const normalizedQuery = query.trim()
  if (!normalizedQuery) {
    return []
  }

  const params = new URLSearchParams({
    q: normalizedQuery,
    format: "jsonv2",
    addressdetails: "1",
    limit: String(options.limit ?? 5),
  })

  if (options.countryCode) {
    params.set("countrycodes", options.countryCode)
  }

  const contactEmail = import.meta.env.VITE_NOMINATIM_EMAIL?.trim()
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
    placeId: item.place_id,
    displayName: item.display_name,
    lat: Number(item.lat),
    lon: Number(item.lon),
  }))
}

export async function reverseGeocode(
  [latitude, longitude]: LatLngTuple,
  options: ReverseGeocodeOptions = {}
): Promise<string | null> {
  const params = new URLSearchParams({
    format: "jsonv2",
    lat: String(latitude),
    lon: String(longitude),
    addressdetails: "1",
    zoom: "18",
  })

  const contactEmail = import.meta.env.VITE_NOMINATIM_EMAIL?.trim()
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
