import { useEffect, useRef, useState } from "react"

import type { StopSearchResult } from "@/features/map/domain/types"
import { searchStops } from "@/features/map/services/stops/stopsService"

type UseStopSearchResult = {
  results: StopSearchResult[]
  isSearching: boolean
  hasAttempted: boolean
  errorMessage: string | null
}

const SEARCH_DEBOUNCE_MS = 450
const MIN_SEARCH_QUERY_LENGTH = 3

export function useStopSearch(query: string, enabled = true): UseStopSearchResult {
  const cacheRef = useRef(new Map<string, StopSearchResult[]>())
  const [results, setResults] = useState<StopSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasAttempted, setHasAttempted] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const normalizedQuery = query.trim()

    if (!enabled || normalizedQuery.length < MIN_SEARCH_QUERY_LENGTH) {
      setResults([])
      setIsSearching(false)
      setHasAttempted(false)
      setErrorMessage(null)
      return
    }

    const cachedResults = cacheRef.current.get(normalizedQuery.toLowerCase())
    if (cachedResults) {
      setResults(cachedResults)
      setIsSearching(false)
      setHasAttempted(true)
      setErrorMessage(null)
      return
    }

    const controller = new AbortController()
    const timeoutId = window.setTimeout(async () => {
      setIsSearching(true)
      setErrorMessage(null)

      try {
        const nextResults = await searchStops(normalizedQuery, {
          limit: 8,
          signal: controller.signal,
        })
        cacheRef.current.set(normalizedQuery.toLowerCase(), nextResults)
        setResults(nextResults)
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return
        }

        setResults([])
        setErrorMessage(
          error instanceof Error ? error.message : "Unable to search bus stops."
        )
      } finally {
        setIsSearching(false)
        setHasAttempted(true)
      }
    }, SEARCH_DEBOUNCE_MS)

    return () => {
      controller.abort()
      window.clearTimeout(timeoutId)
    }
  }, [enabled, query])

  return {
    results,
    isSearching,
    hasAttempted,
    errorMessage,
  }
}

export default useStopSearch
