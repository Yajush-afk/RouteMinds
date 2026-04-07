import { useCallback, useMemo, useState } from "react"

import type { PlaceSuggestion } from "@/features/map/domain/types"
import { useDestinationSearch } from "@/features/map/hooks/useDestinationSearch"

type UseMapSearchStateOptions = {
  onOriginSelect: (result: PlaceSuggestion) => void
  onDestinationSelect: (result: PlaceSuggestion) => void
}

export function useMapSearchState({
  onOriginSelect,
  onDestinationSelect,
}: UseMapSearchStateOptions) {
  const [originLabel, setOriginLabel] = useState("")

  const {
    searchQuery: originSearchQuery,
    setSearchQuery: setOriginSearchQuery,
    results: originResults,
    isSearching: isOriginSearching,
    hasAttempted: hasOriginAttempted,
    clearResults: clearOriginResults,
    selectSuggestion: selectOriginSuggestion,
  } = useDestinationSearch()

  const {
    searchQuery: destinationSearchQuery,
    setSearchQuery: setDestinationSearchQuery,
    results: destinationResults,
    isSearching: isDestinationSearching,
    hasAttempted: hasDestinationAttempted,
    clearResults: clearDestinationResults,
    selectSuggestion: selectDestinationSuggestion,
  } = useDestinationSearch()

  const handleLocationChange = useCallback(
    (nextLocation: string) => {
      setOriginLabel(nextLocation)
      setOriginSearchQuery(nextLocation)

      if (!nextLocation.trim()) {
        clearOriginResults()
      }
    },
    [clearOriginResults, setOriginSearchQuery]
  )

  const handleOriginFocus = useCallback(() => {}, [])

  const handleOriginBlur = useCallback(() => {
    clearOriginResults()
  }, [clearOriginResults])

  const handleOriginSelect = useCallback(
    (result: PlaceSuggestion) => {
      selectOriginSuggestion(result.label)
      setOriginLabel(result.label)
      onOriginSelect(result)
    },
    [onOriginSelect, selectOriginSuggestion]
  )

  const handleDestinationChange = useCallback(
    (nextDestination: string) => {
      setDestinationSearchQuery(nextDestination)

      if (!nextDestination.trim()) {
        clearDestinationResults()
      }
    },
    [clearDestinationResults, setDestinationSearchQuery]
  )

  const handleDestinationFocus = useCallback(() => {}, [])

  const handleDestinationSelect = useCallback(
    (result: PlaceSuggestion) => {
      selectDestinationSuggestion(result.label)
      onDestinationSelect(result)
    },
    [onDestinationSelect, selectDestinationSuggestion]
  )

  const searchPanelProps = useMemo(
    () => ({
      originText: originLabel,
      originResults,
      isOriginSearching,
      showNoOriginResults:
        hasOriginAttempted &&
        originSearchQuery.trim().length >= 3 &&
        originResults.length === 0,
      destinationText: destinationSearchQuery,
      destinationResults,
      isDestinationSearching,
      showNoDestinationResults:
        hasDestinationAttempted &&
        destinationSearchQuery.trim().length >= 3 &&
        destinationResults.length === 0,
      onOriginChange: handleLocationChange,
      onOriginFocus: handleOriginFocus,
      onOriginBlur: handleOriginBlur,
      onOriginSelect: handleOriginSelect,
      onDestinationChange: handleDestinationChange,
      onDestinationFocus: handleDestinationFocus,
      onDestinationSelect: handleDestinationSelect,
    }),
    [
      destinationResults,
      destinationSearchQuery,
      handleDestinationChange,
      handleDestinationFocus,
      handleDestinationSelect,
      handleLocationChange,
      handleOriginBlur,
      handleOriginFocus,
      handleOriginSelect,
      hasDestinationAttempted,
      hasOriginAttempted,
      isDestinationSearching,
      isOriginSearching,
      originLabel,
      originResults,
      originSearchQuery,
    ]
  )

  return {
    searchPanelProps,
  }
}

export default useMapSearchState
