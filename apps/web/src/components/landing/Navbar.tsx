import { useEffect, useState } from "react"
import { Link } from "react-router-dom"

import { Button } from "@workspace/ui/components/button"
import { cn } from "@workspace/ui/lib/utils"

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
    <nav className="fixed inset-x-0 top-0 z-50 px-4 pt-4 md:px-6">
      <div
        className={cn(
          "mx-auto flex max-w-7xl items-center justify-between rounded-xl bg-background/75 px-5 py-3 backdrop-blur-md transition-[border-color,box-shadow,background-color] duration-200",
          isScrolled
            ? "border border-border/50 shadow-sm"
            : "border border-transparent shadow-none"
        )}
      >
        <Link
          to="/"
          className="landing-heading text-lg tracking-tight text-foreground md:text-xl"
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

        <Button
          type="button"
          variant="outline"
          size="lg"
          className="landing-hover-lift rounded-xl border-border bg-transparent px-6 text-foreground shadow-none hover:!border-[var(--landing-primary)] hover:!bg-[var(--landing-primary)] hover:!text-[var(--landing-text)]"
        >
          Sign Up
        </Button>
      </div>
    </nav>
  )
}
