import { useState, useEffect } from "react"
import { Link } from "react-router-dom"

import { useRouteMindsAuth } from "@/auth/useRouteMindsAuth"
import { Button } from "@workspace/ui/components/button"

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
    <nav className="w-full px-4 py-4 sm:px-6 md:px-10 lg:px-24"
    style={{ backgroundColor: "white" }}>
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
          {isConfigured && isAuthenticated ? (
            <>
              <Button
                asChild
                variant="outline"
                className="!font-body rounded-[12px] landing-hover-lift bg-black text-white shadow-2xl hover:!bg-gray-900 border border-zinc-300"
              >
                <Link to="/map">Open Map</Link>
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={logout}
                className="font-body flex landing-hover-lift items-center gap-2 rounded-[12px] border-foreground/20 bg-background shadow-2xl px-4 text-sm text-foreground transition-colors hover:bg-foreground/5 sm:px-5 border border-zinc-300"
              >
                Log out
              </Button>
            </>
          ) : (
            <>
              <Button
                asChild
                variant="ghost"
                className="font-body flex landing-hover-lift items-center gap-2 rounded-[12px] border-foreground/20 bg-background shadow-2xl px-4 text-sm text-foreground transition-colors hover:bg-foreground/5 sm:px-5 border border-zinc-300" >
                <Link to="/auth">Log In</Link>
              </Button>
              <Button
                asChild
                
                className="!font-body rounded-[12px] landing-hover-lift bg-black text-white shadow-2xl hover:!bg-gray-900 border border-zinc-300"
              >
                <Link to="/auth">Get Started</Link>
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="mx-auto mt-4 max-w-7xl border-t border-border" />
    </nav>
  )
}