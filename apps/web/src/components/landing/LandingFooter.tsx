import { FaGithub } from "react-icons/fa"
import { FaXTwitter } from "react-icons/fa6"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Separator } from "@/components/ui/separator"
import { motion } from "motion/react"
import {
  fadeUp,
  landingViewport,
  staggerContainer,
} from "@/components/landing/motion"

const footerSocialItems = [
  {
    label: "X",
    menuLabel: "Creators",
    actions: [
      { label: "@yajush_who", href: "https://x.com/Yajush_who" },
      { label: "@fuzzykny", href: "https://x.com/fuzzykny" },
      { label: "@iamtanuuuu", href: "https://x.com/iamtanuuuu" },
      { label: "@MaheshGoya77594", href: "https://x.com/damngruz" },
    ],
    icon: FaXTwitter,
  },
  {
    label: "GitHub",
    menuLabel: "Contributors",
    actions: [
      { label: "Tanu Singh", href: "https://github.com/tanusingh28" },
      { label: "Yajush", href: "https://github.com/Yajush-afk" },
      { label: "Kritiraj", href: "https://github.com/fuzzyKenny" },
    ],
    icon: FaGithub,
  },
]

export function LandingFooter() {
  return (
    <>
      <motion.footer
        className="bg-background"
        initial="hidden"
        whileInView="visible"
        viewport={landingViewport}
        variants={staggerContainer(0.08, 0.14)}
      >
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
          <motion.div variants={fadeUp(24, 0.65)}>
            <p className="inline-flex items-center gap-2 text-base font-semibold tracking-tight text-foreground">
              <img
                src="/favicon-monochrome.svg"
                alt=""
                className="size-5"
                aria-hidden="true"
              />
              <span>RouteMinds</span>
            </p>
            <p className="mt-1">
              AI-powered transit planning for Delhi commuters.
            </p>
            <div className="mt-3 flex gap-2">
              {footerSocialItems.map(
                ({ label, menuLabel, actions, icon: Icon }) => (
                  <DropdownMenu key={label}>
                    <DropdownMenuTrigger
                      className="flex size-8 items-center justify-center rounded-lg border border-zinc-200 transition-colors duration-200 hover:bg-zinc-100"
                      aria-label={label}
                      title={label}
                    >
                      <Icon className="size-3.5" />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="start"
                      sideOffset={8}
                      className="w-40"
                    >
                      <DropdownMenuGroup>
                        <DropdownMenuLabel>{menuLabel}</DropdownMenuLabel>
                        {actions.map(({ label: actionLabel, href }, index) => (
                          <div key={actionLabel}>
                            <DropdownMenuItem
                              onClick={() =>
                                window.open(
                                  href,
                                  "_blank",
                                  "noopener,noreferrer"
                                )
                              }
                            >
                              {actionLabel}
                            </DropdownMenuItem>
                            {index < actions.length - 1 ? (
                              <DropdownMenuSeparator />
                            ) : null}
                          </div>
                        ))}
                      </DropdownMenuGroup>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )
              )}
            </div>
          </motion.div>

          <motion.div
            className="flex flex-col items-start gap-2"
            variants={fadeUp(24, 0.65)}
          >
            <a href="/#features" className="transition hover:text-foreground">
              Features
            </a>
            <a
              href="https://github.com/yajush-afk/routeminds"
              target="_blank"
              rel="noreferrer"
              className="transition hover:text-foreground"
            >
              GitHub
            </a>
          </motion.div>
        </div>
      </motion.footer>

      <motion.div
        className="bg-background pb-6"
        initial="hidden"
        whileInView="visible"
        viewport={landingViewport}
        variants={fadeUp(20, 0.6)}
      >
        <div className="mx-auto w-full max-w-6xl px-6">
          <Separator />
          <p className="pt-4 text-right text-sm text-muted-foreground">
            © 2026 RouteMinds. All rights reserved.
          </p>
        </div>
      </motion.div>
    </>
  )
}
