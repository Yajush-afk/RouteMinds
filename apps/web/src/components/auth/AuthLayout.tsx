import type { ReactNode } from "react"

import AuthHero from "@/components/auth/AuthHero"

type AuthLayoutProps = {
  children: ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen bg-[#f3f1ea]">
      <div className="relative hidden h-screen w-[58%] shrink-0 overflow-hidden lg:sticky lg:top-0 lg:block">
        <AuthHero />
      </div>

      <div className="flex min-h-screen w-full items-center justify-center bg-[#fcfbf8] px-4 py-10 sm:px-6 lg:w-[42%] lg:px-10">
        {children}
      </div>
    </div>
  )
}
