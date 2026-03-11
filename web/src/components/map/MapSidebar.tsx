import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
} from "@/components/ui/sidebar"
import type { SearchPlaceResult } from "@/lib/nominatim"
import { Input } from "../ui/input"
import { Field } from "../ui/field"

type MapSidebarProps = {
  location: string
  destination: string
  destinationSuggestions: SearchPlaceResult[]
  isDestinationSearching: boolean
  showNoDestinationResults: boolean
  onLocationChange: (nextLocation: string) => void
  onDestinationChange: (nextDestination: string) => void
  onDestinationSelect: (result: SearchPlaceResult) => void
}

function MapSidebar({
  location,
  destination,
  destinationSuggestions,
  isDestinationSearching,
  showNoDestinationResults,
  onLocationChange,
  onDestinationChange,
  onDestinationSelect,
}: MapSidebarProps) {
  return (
    <Sidebar variant="floating" collapsible="offcanvas">
      <SidebarHeader />
      <SidebarContent>
        <SidebarGroup>
          <Field>
            <div>
              <Input
                type="text"
                id="from"
                placeholder="Your location"
                value={location}
                onChange={(event) => onLocationChange(event.target.value)}
              />
            </div>
            <div className="relative">
              <Input
                type="text"
                id="to"
                placeholder="Choose Destination"
                value={destination}
                autoComplete="off"
                onChange={(event) => onDestinationChange(event.target.value)}
              />
              {(isDestinationSearching ||
                destinationSuggestions.length > 0 ||
                showNoDestinationResults) && (
                <div className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border bg-background shadow-md">
                  {isDestinationSearching && (
                    <p className="px-3 py-2 text-sm text-muted-foreground">
                      Searching destinations...
                    </p>
                  )}
                  {!isDestinationSearching &&
                    destinationSuggestions.map((result) => (
                      <button
                        key={result.placeId}
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm hover:bg-accent"
                        onClick={() => onDestinationSelect(result)}
                      >
                        {result.displayName}
                      </button>
                    ))}
                  {!isDestinationSearching &&
                    showNoDestinationResults &&
                    destinationSuggestions.length === 0 && (
                      <p className="px-3 py-2 text-sm text-muted-foreground">
                        No destinations found in Delhi.
                      </p>
                    )}
                </div>
              )}
            </div>
          </Field>
        </SidebarGroup>
        <SidebarGroup />
      </SidebarContent>
      <SidebarFooter />
    </Sidebar>
  )
}

export default MapSidebar
