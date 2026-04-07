import { useState, useEffect } from "react"
import { Link } from "react-router-dom"

import { Button } from "@workspace/ui/components/button"

export default function Navbar() {
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
    <nav className="w-full px-4 py-4 sm:px-6 md:px-10 lg:px-24"
    style={{ backgroundColor: "#fef3c7" }}>
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        {/* Logo */}
        <Link
          to="/"
          className="font-heading text-base tracking-tight text-foreground sm:text-lg md:text-xl"
        >
          RouteMinds
        </Link>

        {/* Nav links */}
        <div className="hidden items-center gap-8 md:flex">
          <a
            href="#about"
            className="font-body text-sm text-foreground transition-colors hover:text-foreground/70"
          >
            About
          </a>
          <a
            href="#features"
            className="font-body text-sm text-foreground transition-colors hover:text-foreground/70"
          >
            Features
          </a>
          <a
            href="#why-delhi"
            className="font-body text-sm text-foreground transition-colors hover:text-foreground/70"
          >
            Why Delhi?
          </a>
          <a
            href="#faqs"
            className="font-body text-sm text-foreground transition-colors hover:text-foreground/70"
          >
            FAQs
          </a>
        </div>

        {/* Right side buttons */}
        <div className="flex items-center gap-2">
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
        </div>
      </div>

      {/* Bottom separator line */}
      <div className="mx-auto mt-4 max-w-7xl border-t border-border" />
    </nav>
  )
}