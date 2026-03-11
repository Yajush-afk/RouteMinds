import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
} from "@/components/ui/sidebar"
import { Input } from "../ui/input"
import { Field } from "../ui/field"

type MapSidebarProps = {
  location: string
  destination: string
  onLocationChange: (nextLocation: string) => void
  onDestinationChange: (nextDestination: string) => void
}

function MapSidebar({
  location,
  destination,
  onLocationChange,
  onDestinationChange,
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
            <div>
              <Input
                type="text"
                id="to"
                placeholder="Choose Destination"
                value={destination}
                onChange={(event) => onDestinationChange(event.target.value)}
              />
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
