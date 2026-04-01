import { memo, type ComponentProps } from "react"

import MapSearchBar from "@/features/map/components/search/MapSearchBar"

type MapSearchPanelProps = ComponentProps<typeof MapSearchBar>

function MapSearchPanel(props: MapSearchPanelProps) {
  return (
    <div className="pointer-events-none absolute inset-0 z-850">
      <MapSearchBar {...props} />
    </div>
  )
}

export default memo(MapSearchPanel)
