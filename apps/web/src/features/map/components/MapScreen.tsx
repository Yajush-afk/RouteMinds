import { LoaderCircle, MonitorSmartphone } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { useRouteMindsAuth } from "@/auth/useRouteMindsAuth"
import MapViewport from "@/features/map/components/MapViewport"
import MapRouteSidebar from "@/features/map/components/sidebar/MapRouteSidebar"
import { useMapScreenState } from "@/features/map/hooks/useMapScreenState"
import { SidebarInset, SidebarProvider } from "@workspace/ui/components/sidebar"
import { useIsMobile } from "@workspace/ui/hooks/use-mobile"

const MAP_SPINNER_DELAY_MS = 400

function MapScreen() {
  const isMobile = useIsMobile()

  if (isMobile) {
    return (
      <section className="relative flex h-screen w-full items-center justify-center overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(14,165,233,0.12),_transparent_42%),linear-gradient(180deg,_#f8fbff_0%,_#eef5ff_100%)] px-6">
        <div className="absolute inset-x-6 top-10 h-px bg-gradient-to-r from-transparent via-sky-300/70 to-transparent" />
        <div className="relative w-full max-w-sm rounded-[2rem] border border-sky-100/80 bg-white/88 p-7 text-center shadow-[0_24px_80px_-28px_rgba(15,23,42,0.32)] backdrop-blur-xl">
          <div className="mx-auto mb-5 grid size-14 place-items-center rounded-2xl bg-sky-50 text-sky-600 shadow-[inset_0_0_0_1px_rgba(14,165,233,0.12)]">
            <MonitorSmartphone className="size-7" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-pretty text-slate-900">
            Map is desktop only
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            The live map experience is disabled on mobile displays. Open
            RouteMinds on a tablet or desktop-sized screen to use map search,
            markers, and route preview.
          </p>
        </div>
      </section>
    )
  }

  return <DesktopMapScreen />
}

function DesktopMapScreen() {
  const { logout, user } = useRouteMindsAuth()
  const { mapViewportProps, sidebarProps } = useMapScreenState()
  const [isMapReady, setIsMapReady] = useState(false)
  const [shouldShowSpinner, setShouldShowSpinner] = useState(false)
  const delayTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    delayTimeoutRef.current = window.setTimeout(() => {
      setShouldShowSpinner(true)
    }, MAP_SPINNER_DELAY_MS)

    return () => {
      if (delayTimeoutRef.current !== null) {
        window.clearTimeout(delayTimeoutRef.current)
      }
    }
  }, [])

  function handleMapReady() {
    setIsMapReady(true)
    setShouldShowSpinner(false)

    if (delayTimeoutRef.current !== null) {
      window.clearTimeout(delayTimeoutRef.current)
      delayTimeoutRef.current = null
    }
  }

  return (
    <section className="h-screen w-full">
      <SidebarProvider width="24rem" className="relative h-full">
        <MapRouteSidebar {...sidebarProps} user={user} onSignOut={logout} />
        <SidebarInset className="bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.12),_transparent_32%),linear-gradient(180deg,_#edf5ff_0%,_#f8fbff_24%,_#ffffff_100%)]">
          <MapViewport {...mapViewportProps} onMapReady={handleMapReady} />
          {shouldShowSpinner && !isMapReady ? (
            <div className="absolute inset-0 z-950 grid place-items-center bg-background/72 backdrop-blur-[2px]">
              <div className="flex flex-col items-center gap-3 rounded-2xl bg-card/92 px-6 py-5 text-card-foreground shadow-lg ring-1 ring-border/60">
                <LoaderCircle className="size-6 animate-spin text-sky-600" />
                <p className="text-sm font-medium">Loading map</p>
              </div>
            </div>
          ) : null}
        </SidebarInset>
      </SidebarProvider>
    </section>
  )
}

export default MapScreen
