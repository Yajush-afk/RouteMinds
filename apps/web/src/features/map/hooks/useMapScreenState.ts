import { useMultiStopRoutePlanner } from "@/features/map/hooks/useMultiStopRoutePlanner"

export function useMapScreenState() {
  return useMultiStopRoutePlanner()
}

export default useMapScreenState
