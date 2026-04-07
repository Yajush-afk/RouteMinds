import { Link } from "react-router-dom"
import { motion } from "motion/react"
import { useEffect, useState } from "react"

import { Button } from "@workspace/ui/components/button"

export default function HeroSection() {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)")
    const updateIsMobile = () => setIsMobile(mediaQuery.matches)

    updateIsMobile()
    mediaQuery.addEventListener("change", updateIsMobile)

    return () => mediaQuery.removeEventListener("change", updateIsMobile)
  }, [])

  return (
    <section
      id="about"
      className=" px-4 pt-24 pb-16 sm:px-6 sm:pt-28 sm:pb-20 md:px-10 md:pt-32 lg:px-24"
      style={{ background: "linear-gradient(to bottom, #fef3c7, white)" }}
    >
      <div className="mx-auto mt-12 grid w-full max-w-7xl grid-cols-1 items-center gap-10 sm:mt-16 sm:gap-12 md:mt-24 md:grid-cols-2 md:gap-16">
        {/* Left Side */}
        <div className="space-y-4 text-center md:text-left">
          {/* Heading */}
          <div>
            <motion.h1
              className=" font-heading font-bold text-4xl leading-tight text-foreground sm:text-5xl md:text-6xl"
              initial={{ opacity: 0, x: isMobile ? -16 : -40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                duration: isMobile ? 0.55 : 0.8,
                ease: "easeInOut",
              }}
            >
              Stop Waiting.
            </motion.h1>
            <motion.h1
              className="font-heading font-bold text-4xl leading-tight text-[#5a2d14] sm:text-5xl md:text-6xl"
              initial={{ opacity: 0, x: isMobile ? -16 : -40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                duration: isMobile ? 0.55 : 0.8,
                ease: "easeInOut",
              }}
            >
              Start Predicting.
            </motion.h1>
          </div>

          {/* Description */}
          <p className="font-body mx-auto -mt-1 mb-8 max-w-md text-base leading-relaxed text-muted-foreground sm:mb-10 sm:text-lg md:mx-0">
            Plan your journey in advance with AI-powered delay predictions based
            on real traffic patterns in Delhi.
          </p>

          {/* Buttons */}
          <div className=" flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:gap-4 md:justify-start">
            <Button
            asChild
            size="lg"
            className="!font-heading rounded-[12px] landing-hover-lift  w-full justify-center gap-2 px-6 py-5 sm:w-auto sm:px-8 sm:py-6 sm:text-lg bg-black text-white shadow-2xl hover:!bg-gray-900 border border-zinc-300"
          >
          <Link to="/map">
           Get Started
          <svg
           stroke="currentColor"
           fill="currentColor"
           strokeWidth="0"
           viewBox="0 0 448 512"
           className="size-3.5 -rotate-45"
           height="1em"
           width="1em"
           xmlns="http://www.w3.org/2000/svg"
          >
          <path d="M438.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-160-160c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L338.8 224 32 224c-17.7 0-32 14.3-32 32s14.3 32 32 32l306.7 0L233.4 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l160-160z" />
          </svg>
     </Link>
            </Button>
            <Button
              asChild
              variant="ghost"
              size="lg"
              className="  !font-heading landing-hover-lift shadow-2xl w-full justify-center px-6 py-5 text-base sm:w-auto sm:px-8 sm:py-6 sm:text-lg border border-zinc-300"
            >
              <Link to="/map">
              View Map
              <svg
             stroke="currentColor"
             fill="currentColor"
             strokeWidth="0"
             viewBox="0 0 448 512"
             className="size-3.5 -rotate-45"
             height="1em"
             width="1em"
             xmlns="http://www.w3.org/2000/svg"
            >
            <path d="M438.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-160-160c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L338.8 224 32 224c-17.7 0-32 14.3-32 32s14.3 32 32 32l306.7 0L233.4 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l160-160z" />
             </svg>
            </Link>
            </Button>
          </div>
        </div>

        {/* Right Side - Stats Card */}
        <div className="mx-auto w-full max-w-sm rounded-2xl bg-secondary p-5 text-foreground shadow-2xl sm:max-w-md sm:p-6 md:max-w-none">
          <p className="font-body text-xs tracking-widest text-muted-foreground uppercase">
            Route and Prediction
          </p>
          <div>
            <p className="font-heading text-3xl sm:text-4xl">12m Delay</p>
            <p className="font-body mt-1 text-sm text-muted-foreground">
              High Congestion at ITO
            </p>
          </div>
          <div className="border-t border-border pt-4">
            <p className="font-body text-xs tracking-widest text-muted-foreground uppercase">
              Confidence Score
            </p>
            <p className="font-heading mt-1 text-4xl text-[#78350f] sm:text-5xl">
              94.4%
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
