import { useMapPlacementState } from "@/features/map/hooks/useMapPlacementState"
import { useMapSearchState } from "@/features/map/hooks/useMapSearchState"

export function useMapScreenState() {
  const placementState = useMapPlacementState()

  const searchState = useMapSearchState({
    onOriginSelect: placementState.handleOriginSelect,
    onDestinationSelect: placementState.handleDestinationSelect,
  })

  return {
    mapViewportProps: placementState.mapViewportProps,
    searchPanelProps: searchState.searchPanelProps,
  }
}

export default useMapScreenState
