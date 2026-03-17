import type { LatLngTuple } from "leaflet"

export async function getBrowserLocation(): Promise<LatLngTuple> {
  if (!navigator.geolocation) {
    throw new Error("Geolocation is not supported by this browser.")
  }

  return new Promise<LatLngTuple>((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve([position.coords.latitude, position.coords.longitude])
      },
      () => {
        reject(new Error("Unable to retrieve your location."))
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
      }
    )
  })
}
