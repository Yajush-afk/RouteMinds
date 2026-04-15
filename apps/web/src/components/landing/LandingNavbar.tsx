import type { MouseEvent } from "react"
import { LogOut } from "lucide-react"
import { FaGithub } from "react-icons/fa"
import { motion } from "motion/react"
import { Link } from "react-router-dom"
import { useRouteMindsAuth } from "@/auth/useRouteMindsAuth"
import { fadeIn, fadeUp } from "@/components/landing/motion"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@workspace/ui/components/avatar"

function getSectionOffset(sectionId: string) {
  return sectionId === "why-delhi" ? 24 : 80
}

function getAvatarFallback(name?: string, email?: string) {
  const words = (name ?? "")
    .trim()
    .split(/\s+/)
    .map((word) => word.replace(/[^a-z0-9]/gi, ""))
    .filter(Boolean)

  if (words.length >= 2) {
    return `${words[0][0]}${words[1][0]}`.slice(0, 2).toUpperCase()
  }

  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase()
  }

  const emailLocalPart = (email ?? "")
    .split("@")[0]
    ?.replace(/[^a-z0-9]/gi, "")
    .trim()

  if (emailLocalPart) {
    return emailLocalPart.slice(0, 2).toUpperCase()
  }

  return "RM"
}

function NavbarAuthAction({ mobile = false }: { mobile?: boolean }) {
  const { error, isAuthenticated, isConfigured, isLoading, logout, user } =
    useRouteMindsAuth()
  const signupClassName = mobile
    ? "inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-medium text-black transition hover:bg-white/90"
    : "inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-white/90"
  const avatarSizeClassName = mobile ? "size-9" : "size-10"
  const avatarFallback = getAvatarFallback(user?.name, user?.email)
  const triggerTitle = user?.name ?? user?.email ?? "Account menu"

  if (!isConfigured || error) {
    return (
      <Link to="/map" className={signupClassName}>
        SignUp
      </Link>
    )
  }

  if (isLoading) {
    return (
      <div
        aria-hidden="true"
        className={`${avatarSizeClassName} rounded-full border border-white/20 bg-white/12 backdrop-blur-sm`}
      />
    )
  }

  if (!isAuthenticated) {
    return (
      <Link to="/map" className={signupClassName}>
        SignUp
      </Link>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        title={triggerTitle}
        className={`inline-flex ${avatarSizeClassName} items-center justify-center rounded-full border border-white/20 bg-white/12 p-0 text-white shadow-[0_10px_30px_rgba(0,0,0,0.18)] backdrop-blur-sm transition hover:bg-white/18 focus-visible:ring-2 focus-visible:ring-white/60 focus-visible:outline-none`}
      >
        <Avatar className="size-full">
          <AvatarImage src={user?.picture} alt={triggerTitle} />
          <AvatarFallback className="bg-white/90 text-xs font-semibold tracking-[0.14em] text-black">
            {avatarFallback}
          </AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={8} className="w-36">
        <DropdownMenuItem
          onClick={() => {
            void logout()
          }}
        >
          <LogOut className="size-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function LandingNavbar() {
  const handleSectionClick =
    (sectionId: string) => (event: MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault()

      const target = document.getElementById(sectionId)
      if (!target) {
        return
      }

      const targetTop =
        target.getBoundingClientRect().top +
        window.scrollY +
        getSectionOffset(sectionId)

      window.scrollTo({ top: targetTop, behavior: "smooth" })
    }

  return (
    <motion.header
      className="pointer-events-none absolute inset-x-0 top-4 z-50"
      initial="hidden"
      animate="visible"
      variants={fadeIn(0.55)}
    >
      <motion.nav
        className="pointer-events-auto relative mx-auto flex w-[min(92%,64rem)] flex-col gap-3 rounded-3xl px-4 py-3 md:flex-row md:items-center md:justify-between md:rounded-4xl md:px-5"
        variants={fadeUp(18, 0.65)}
      >
        <motion.div
          className="flex w-full items-center justify-between md:w-auto md:justify-start"
          variants={fadeUp(16, 0.55)}
        >
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-xl font-semibold tracking-tight text-white sm:text-2xl"
          >
            <img
              src="/favicon.svg"
              alt=""
              className="size-6"
              aria-hidden="true"
            />
            <span>RouteMinds</span>
          </Link>

          <div className="flex items-center gap-2 text-sm md:hidden">
            <a
              href="https://github.com/yajush-afk/routeminds"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-black px-3 py-2 text-sm font-medium text-white transition hover:bg-black/90"
            >
              <FaGithub className="size-4" />
              <span className="hidden sm:inline">GitHub</span>
            </a>
            <NavbarAuthAction mobile />
          </div>
        </motion.div>

        <motion.div
          className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 md:flex"
          variants={fadeUp(16, 0.55)}
        >
          <a
            href="/#features"
            onClick={handleSectionClick("features")}
            className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Features
          </a>
          <a
            href="/#why-delhi"
            onClick={handleSectionClick("why-delhi")}
            className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Why Delhi
          </a>
          <a
            href="/#faq"
            onClick={handleSectionClick("faq")}
            className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            FAQ
          </a>
        </motion.div>

        <motion.div
          className="hidden w-full items-center gap-1 overflow-x-auto text-sm md:hidden"
          variants={fadeUp(16, 0.55)}
        >
          <a
            href="/#features"
            onClick={handleSectionClick("features")}
            className="inline-flex shrink-0 items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Features
          </a>
          <a
            href="/#why-delhi"
            onClick={handleSectionClick("why-delhi")}
            className="inline-flex shrink-0 items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Why Delhi
          </a>
          <a
            href="/#faq"
            onClick={handleSectionClick("faq")}
            className="inline-flex shrink-0 items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            FAQ
          </a>
        </motion.div>

        <motion.div
          className="hidden items-center gap-2 text-sm md:flex"
          variants={fadeUp(16, 0.55)}
        >
          <a
            href="https://github.com/yajush-afk/routeminds"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-black/90"
          >
            <FaGithub className="size-4" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <NavbarAuthAction />
        </motion.div>
      </motion.nav>
    </motion.header>
  )
}
