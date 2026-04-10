import { useEffect, useState } from "react"
import { Link } from "react-router-dom"

import { useRouteMindsAuth } from "@/auth/useRouteMindsAuth"
import { Button } from "@workspace/ui/components/button"
import { cn } from "@workspace/ui/lib/utils"

export default function Navbar() {
  const { isAuthenticated, isConfigured, logout } = useRouteMindsAuth()
  const [isScrolled, setIsScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 12)
    }

    handleScroll()
    window.addEventListener("scroll", handleScroll, { passive: true })

    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <nav className="fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-4 md:px-6">
      <div
        className={cn(
          "mx-auto flex max-w-7xl items-center justify-between rounded-xl bg-background/75 px-4 py-2.5 backdrop-blur-md transition-[border-color,box-shadow,background-color] duration-200 sm:px-5 sm:py-3",
          isScrolled
            ? "border border-border/50 shadow-sm"
            : "border border-transparent shadow-none"
        )}
      >
        <Link
          to="/"
          className="landing-heading text-base tracking-tight text-foreground sm:text-lg md:text-xl"
        >
          RouteMinds
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          <a
            href="#about"
            className="text-sm text-foreground transition-colors hover:text-primary"
          >
            About
          </a>
          <a
            href="#features"
            className="text-sm text-foreground transition-colors hover:text-primary"
          >
            Features
          </a>
          <a
            href="#why-delhi"
            className="text-sm text-foreground transition-colors hover:text-primary"
          >
            Why Delhi?
          </a>
          <a
            href="#faqs"
            className="text-sm text-foreground transition-colors hover:text-primary"
          >
            FAQs
          </a>
        </div>

        <div className="flex items-center gap-2">
          {isConfigured && isAuthenticated ? (
            <>
              <Button
                asChild
                variant="outline"
                className="landing-hover-lift rounded-xl border-border bg-transparent px-4 text-sm text-foreground shadow-none hover:!border-[var(--landing-primary)] hover:!bg-[var(--landing-primary)] hover:!text-[var(--landing-text)] sm:px-5 md:px-6"
              >
                <Link to="/map">Open Map</Link>
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={logout}
                className="rounded-xl px-4 text-sm text-foreground"
              >
                Log out
              </Button>
            </>
          ) : (
            <>
              <Button
                asChild
                variant="ghost"
                className="rounded-xl px-4 text-sm text-foreground hover:bg-transparent hover:text-[var(--landing-primary)]"
              >
                <Link to="/auth">Log In</Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="landing-hover-lift rounded-xl border-border bg-transparent px-4 text-sm text-foreground shadow-none hover:!border-[var(--landing-primary)] hover:!bg-[var(--landing-primary)] hover:!text-[var(--landing-text)] sm:px-5 md:px-6"
              >
                <Link to="/auth">Get Started</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
