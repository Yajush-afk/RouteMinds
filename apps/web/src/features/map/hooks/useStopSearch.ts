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
const MIN_SEARCH_QUERY_LENGTH = 2
const STOP_SEARCH_CACHE_LIMIT = 100

const sharedStopSearchCache = new Map<string, StopSearchResult[]>()

function readCachedStopSearchResults(query: string) {
  const key = query.toLowerCase()
  const cachedResults = sharedStopSearchCache.get(key)
  if (!cachedResults) {
    return null
  }

  sharedStopSearchCache.delete(key)
  sharedStopSearchCache.set(key, cachedResults)
  return cachedResults
}

function writeCachedStopSearchResults(query: string, results: StopSearchResult[]) {
  const key = query.toLowerCase()
  sharedStopSearchCache.delete(key)
  sharedStopSearchCache.set(key, results)

  if (sharedStopSearchCache.size <= STOP_SEARCH_CACHE_LIMIT) {
    return
  }

  const oldestKey = sharedStopSearchCache.keys().next().value
  if (oldestKey) {
    sharedStopSearchCache.delete(oldestKey)
  }
}

export function useStopSearch(query: string, enabled = true): UseStopSearchResult {
  const activeQueryRef = useRef("")
  const [results, setResults] = useState<StopSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasAttempted, setHasAttempted] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const normalizedQuery = query.trim()

    if (!enabled || normalizedQuery.length < MIN_SEARCH_QUERY_LENGTH) {
      activeQueryRef.current = ""
      setResults([])
      setIsSearching(false)
      setHasAttempted(false)
      setErrorMessage(null)
      return
    }

    activeQueryRef.current = normalizedQuery

    const cachedResults = readCachedStopSearchResults(normalizedQuery)
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
        if (activeQueryRef.current !== normalizedQuery) {
          return
        }
        writeCachedStopSearchResults(normalizedQuery, nextResults)
        setResults(nextResults)
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return
        }

        if (activeQueryRef.current !== normalizedQuery) {
          return
        }
        setResults([])
        setErrorMessage(
          error instanceof Error ? error.message : "Unable to search bus stops."
        )
      } finally {
        if (activeQueryRef.current !== normalizedQuery) {
          return
        }
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
