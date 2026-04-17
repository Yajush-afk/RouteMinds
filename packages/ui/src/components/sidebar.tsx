import * as React from "react"

import { cn } from "@workspace/ui/lib/utils"

type SidebarContextValue = {
  width: string
}

const SidebarContext = React.createContext<SidebarContextValue>({
  width: "24rem",
})

function SidebarProvider({
  className,
  style,
  width = "24rem",
  children,
  ...props
}: React.ComponentProps<"div"> & {
  width?: string
}) {
  return (
    <SidebarContext.Provider value={{ width }}>
      <div
        data-slot="sidebar-provider"
        style={
          {
            ...style,
            ["--sidebar-width" as string]: width,
          } as React.CSSProperties
        }
        className={cn(
          "group/sidebar-wrapper flex min-h-0 w-full flex-1 overflow-hidden bg-background text-foreground",
          className
        )}
        {...props}
      >
        {children}
      </div>
    </SidebarContext.Provider>
  )
}

function Sidebar({
  className,
  children,
  ...props
}: React.ComponentProps<"aside">) {
  const { width } = React.useContext(SidebarContext)

  return (
    <aside
      data-slot="sidebar"
      style={
        {
          ["--sidebar-width" as string]: width,
        } as React.CSSProperties
      }
      className={cn(
        "flex h-full w-[var(--sidebar-width)] shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground",
        className
      )}
      {...props}
    >
      {children}
    </aside>
  )
}

function SidebarHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-header"
      className={cn("flex flex-col gap-4 border-b border-sidebar-border p-5", className)}
      {...props}
    />
  )
}

function SidebarContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-content"
      className={cn("flex min-h-0 flex-1 flex-col overflow-y-auto", className)}
      {...props}
    />
  )
}

function SidebarFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-footer"
      className={cn("border-t border-sidebar-border p-4", className)}
      {...props}
    />
  )
}

function SidebarGroup({
  className,
  ...props
}: React.ComponentProps<"section">) {
  return (
    <section
      data-slot="sidebar-group"
      className={cn("flex flex-col gap-3 px-4 py-5", className)}
      {...props}
    />
  )
}

function SidebarGroupLabel({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-group-label"
      className={cn(
        "px-1 text-[11px] font-semibold tracking-[0.18em] text-sidebar-foreground/60 uppercase",
        className
      )}
      {...props}
    />
  )
}

function SidebarGroupContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-group-content"
      className={cn("flex flex-col gap-3", className)}
      {...props}
    />
  )
}

function SidebarInset({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sidebar-inset"
      className={cn("relative flex min-w-0 flex-1 flex-col overflow-hidden", className)}
      {...props}
    />
  )
}

export {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarProvider,
}
