import type { ReactNode } from "react"
import { ArrowLeft } from "lucide-react"
import { Link } from "react-router-dom"

import AuthHero from "@/components/auth/AuthHero"
import { Button } from "@workspace/ui/components/button"

type AuthLayoutProps = {
  children: ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen bg-[#f3f1ea]">
      <div className="relative hidden h-screen w-[58%] shrink-0 overflow-hidden lg:sticky lg:top-0 lg:block">
        <AuthHero />
      </div>

      <div className="relative flex min-h-screen w-full items-center justify-center bg-[#fcfbf8] px-4 py-10 sm:px-6 lg:w-[42%] lg:px-10">
        <div className="absolute top-5 left-4 sm:top-6 sm:left-6 lg:top-8 lg:left-8">
          <Button
            asChild
            variant="ghost"
            className="rounded-full border border-[#e6e0d3] bg-white/80 px-3 text-[#2f2a22] shadow-sm backdrop-blur-sm hover:bg-white"
          >
            <Link to="/" aria-label="Back to landing page">
              <ArrowLeft className="size-4" />
            </Link>
          </Button>
        </div>

        {children}
      </div>
    </div>
  )
}
