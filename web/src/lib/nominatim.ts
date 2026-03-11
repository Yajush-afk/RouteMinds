import type { LatLngTuple } from "leaflet"

const NOMINATIM_REVERSE_ENDPOINT = "https://nominatim.openstreetmap.org/reverse"

type ReverseGeocodeOptions = {
  signal?: AbortSignal
  language?: string
}

type NominatimReverseResponse = {
  display_name?: string
  error?: string
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
