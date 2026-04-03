import { Link } from "react-router-dom"

import { Button } from "@workspace/ui/components/button"

export default function Navbar() {
  return (
    <nav className="fixed top-4 right-4 left-4 z-50 flex items-center justify-between rounded-2xl border border-border/60 bg-background/80 px-8 py-4 shadow-sm backdrop-blur-md">
      {/* Logo */}
      <Link
        to="/"
        className="landing-heading text-xl tracking-tight text-foreground"
      >
        RouteMinds
      </Link>

      {/* Nav Links */}
      <div className="hidden items-center gap-6 md:flex">
        <a
          href="#about"
          className="text-base text-foreground transition-colors hover:text-primary"
        >
          About
        </a>
        <a
          href="#features"
          className="text-base text-foreground transition-colors hover:text-primary"
        >
          Features
        </a>
        <a
          href="#why-delhi"
          className="text-base text-foreground transition-colors hover:text-primary"
        >
          Why Delhi?
        </a>
        <a
          href="#faqs"
          className="text-base text-foreground transition-colors hover:text-primary"
        >
          FAQs
        </a>
      </div>

      {/* Sign Up Button */}

      <Button
        type="button"
        size="lg"
        className="rounded-xl bg-accent px-8 py-5 text-accent-foreground hover:bg-accent/90"
      >
        Sign Up
      </Button>
    </nav>
  )
}
