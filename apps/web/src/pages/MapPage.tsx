import { useEffect } from "react"
import maplibreStyles from "maplibre-gl/dist/maplibre-gl.css?inline"

import MapScreen from "@/features/map/components/MapScreen"

function MapPage() {
  useEffect(() => {
    let styleTag = document.querySelector<HTMLStyleElement>(
      'style[data-maplibre-styles="true"]'
    )

    if (!styleTag) {
      styleTag = document.createElement("style")
      styleTag.dataset.maplibreStyles = "true"
      styleTag.textContent = maplibreStyles
      document.head.appendChild(styleTag)
    }

    return () => {
      if (styleTag?.dataset.maplibreStyles === "true") {
        styleTag.remove()
      }
    }
  }, [])

  return (
    <main className="flex min-h-screen">
      <MapScreen />
    </main>
  )
}

export default MapPage
