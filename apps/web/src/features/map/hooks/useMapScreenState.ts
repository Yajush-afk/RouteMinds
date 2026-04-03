import { useCallback, useLayoutEffect, useRef } from "react"
import type { LocationField } from "@/features/map/domain/types"
import { useMapPlacementState } from "@/features/map/hooks/useMapPlacementState"
import { useMapSearchState } from "@/features/map/hooks/useMapSearchState"

export function useMapScreenState() {
  const searchLabelControllerRef = useRef<{
    setFieldLabel: (field: LocationField, label: string) => void
  } | null>(null)

  const handleFieldLabelChange = useCallback(
    (field: LocationField, label: string) => {
      searchLabelControllerRef.current?.setFieldLabel(field, label)
    },
    []
  )

  const placementState = useMapPlacementState({
    onFieldLabelChange: handleFieldLabelChange,
  })

  const searchState = useMapSearchState({
    onFieldFocus: placementState.setActiveField,
    onOriginSelect: placementState.handleOriginSelect,
    onDestinationSelect: placementState.handleDestinationSelect,
  })

  useLayoutEffect(() => {
    searchLabelControllerRef.current = {
      setFieldLabel: searchState.setFieldLabel,
    }

    return () => {
      if (
        searchLabelControllerRef.current?.setFieldLabel ===
        searchState.setFieldLabel
      ) {
        searchLabelControllerRef.current = null
      }
    }
  }, [searchState.setFieldLabel])

  return {
    mapViewportProps: placementState.mapViewportProps,
    searchPanelProps: searchState.searchPanelProps,
  }
}

export default useMapScreenState
