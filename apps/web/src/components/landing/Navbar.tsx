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
        
        <Link
          to="/"
          className="font-heading text-base tracking-tight text-foreground sm:text-lg md:text-xl"
        >
          RouteMinds
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          <a
            href="#about"
            className="font-body text-base font-medium text-foreground transition-colors hover:text-foreground/70"
          >
            About
          </a>
          <a
            href="#features"
            className="font-body text-base font-medium text-foreground transition-colors hover:text-foreground/70"
          >
            Features
          </a>
          <a
            href="#why-delhi"
            className="font-body text-base font-medium text-foreground transition-colors hover:text-foreground/70"
          >
            Why Delhi?
          </a>
          <a
            href="#faqs"
            className="font-body text-base font-medium text-foreground transition-colors hover:text-foreground/70"
          >
            FAQs
          </a>
        </div>

       
        <div className="flex items-center gap-2">
          <Button
                asChild
                variant="outline"
                className="font-body flex landing-hover-lift items-center gap-2 rounded-[12px] border-foreground/20 bg-background shadow-2xl px-4 text-sm text-foreground transition-colors hover:bg-foreground/5 sm:px-5 border border-zinc-300"              >
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <svg
                    viewBox="0 0 24 24"
                    className="h-4 w-4 fill-current"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  GitHub
                </a>
              </Button>
          
              <Button
                asChild
                className="font-body rounded-[12px] landing-hover-lift bg-black text-white shadow-2xl hover:!bg-gray-900 border border-zinc-300" >
                <Link to="/auth">Get Started</Link>
              </Button>
        </div>
      </div>

      <div className="mx-auto mt-4 max-w-7xl border-t border-border" />
    </nav>
  )
}