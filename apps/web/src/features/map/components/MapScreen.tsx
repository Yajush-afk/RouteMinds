import { MonitorSmartphone } from "lucide-react"

import MapViewport from "@/features/map/components/MapViewport"
import MapSearchPanel from "@/features/map/components/search/MapSearchPanel"
import { useMapScreenState } from "@/features/map/hooks/useMapScreenState"
import { useIsMobile } from "@workspace/ui/hooks/use-mobile"

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
          <h1 className="text-pretty text-xl font-semibold tracking-tight text-slate-900">
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
  const { mapViewportProps, searchPanelProps } = useMapScreenState()

  return (
    <section className="relative h-screen w-full">
      <MapViewport {...mapViewportProps} />
      <MapSearchPanel {...searchPanelProps} />
    </section>
  )
}

export default MapScreen
