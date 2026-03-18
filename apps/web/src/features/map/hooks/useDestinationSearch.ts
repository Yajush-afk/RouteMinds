import { useEffect, useRef, useState } from "react"

import { DESTINATION_SEARCH_DEBOUNCE_MS } from "@/features/map/domain/mapDefaults"
import { isSelectableLocation } from "@/features/map/domain/locationPolicy"
import type { PlaceSuggestion } from "@/features/map/domain/types"
import { searchPlaces } from "@/features/map/services/places/nominatimPlacesService"

type UseDestinationSearchResult = {
  searchQuery: string
  setSearchQuery: (nextQuery: string) => void
  results: PlaceSuggestion[]
  isSearching: boolean
  hasAttempted: boolean
  clearResults: () => void
  selectSuggestion: (nextQuery: string) => void
}

export function useDestinationSearch(): UseDestinationSearchResult {
  const skipNextSearchRef = useRef(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [results, setResults] = useState<PlaceSuggestion[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasAttempted, setHasAttempted] = useState(false)

  useEffect(() => {
    const normalizedQuery = searchQuery.trim()

    if (normalizedQuery.length < 3) {
      setResults([])
      setIsSearching(false)
      setHasAttempted(false)
      return
    }

    if (skipNextSearchRef.current) {
      skipNextSearchRef.current = false
      setResults([])
      setIsSearching(false)
      setHasAttempted(false)
      return
    }

    const controller = new AbortController()

    const timeoutId = window.setTimeout(async () => {
      setIsSearching(true)

      try {
        const places = await searchPlaces(normalizedQuery, {
          signal: controller.signal,
          countryCode: "in",
          limit: 5,
        })

        const selectableResults = places.filter((place) =>
          isSelectableLocation(place.position)
        )

        setResults(selectableResults)
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return
        }

        setResults([])
      } finally {
        setIsSearching(false)
        setHasAttempted(true)
      }
    }, DESTINATION_SEARCH_DEBOUNCE_MS)

    return () => {
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [searchQuery])

  const clearResults = () => {
    setResults([])
    setHasAttempted(false)
  }

  const selectSuggestion = (nextQuery: string) => {
    skipNextSearchRef.current = true
    setSearchQuery(nextQuery)
    setResults([])
    setIsSearching(false)
    setHasAttempted(false)
  }

  return {
    searchQuery,
    setSearchQuery,
    results,
    isSearching,
    hasAttempted,
    clearResults,
    selectSuggestion,
  }
}

export default useDestinationSearch
