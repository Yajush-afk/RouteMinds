const DEFAULT_OPENFREEMAP_STYLE_URL =
  "https://tiles.openfreemap.org/styles/liberty"

export const OPENFREEMAP_STYLE_URL =
  import.meta.env.VITE_OPENFREEMAP_STYLE_URL?.trim() ||
  DEFAULT_OPENFREEMAP_STYLE_URL

export const OPENFREEMAP_ATTRIBUTION =
  '&copy; <a href="https://openfreemap.org" target="_blank" rel="noreferrer">OpenFreeMap</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>'
