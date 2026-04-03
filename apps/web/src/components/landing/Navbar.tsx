import { Link } from "react-router-dom"

import { Button } from "@workspace/ui/components/button"

export default function Navbar() {
  return (
    <nav className="fixed inset-x-0 top-0 z-50 px-4 pt-4 md:px-6">
      <div className="mx-auto flex max-w-7xl items-center justify-between rounded-xl border border-border/50 bg-background/75 px-5 py-3 shadow-sm backdrop-blur-md">
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
