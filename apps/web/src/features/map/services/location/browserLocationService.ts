import type { LngLat, LocationErrorCode } from "@/features/map/domain/types"

export class BrowserLocationError extends Error {
  public readonly code: LocationErrorCode

  constructor(message: string, code: LocationErrorCode) {
    super(message)
    this.name = "BrowserLocationError"
    this.code = code
  }
}

function mapGeolocationErrorCode(code: number): LocationErrorCode {
  switch (code) {
    case GeolocationPositionError.PERMISSION_DENIED:
      return "PERMISSION_DENIED"
    case GeolocationPositionError.POSITION_UNAVAILABLE:
      return "POSITION_UNAVAILABLE"
    case GeolocationPositionError.TIMEOUT:
      return "TIMEOUT"
    default:
      return "UNKNOWN"
  }
}

function getErrorMessage(code: LocationErrorCode) {
  switch (code) {
    case "UNSUPPORTED":
      return "Geolocation is not supported by this browser."
    case "PERMISSION_DENIED":
      return "Location access was denied."
    case "POSITION_UNAVAILABLE":
      return "Your location is currently unavailable."
    case "TIMEOUT":
      return "Location request timed out."
    case "UNKNOWN":
    default:
      return "Unable to retrieve your location."
  }
}

export async function getCurrentPosition(): Promise<LngLat> {
  if (!navigator.geolocation) {
    throw new BrowserLocationError(
      getErrorMessage("UNSUPPORTED"),
      "UNSUPPORTED"
    )
  }

  return new Promise<LngLat>((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        })
      },
      (error) => {
        const code = mapGeolocationErrorCode(error.code)
        reject(new BrowserLocationError(getErrorMessage(code), code))
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
      }
    )
  })
}
