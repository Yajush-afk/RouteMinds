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
      className="bg-background px-4 pt-24 pb-16 sm:px-6 sm:pt-28 sm:pb-20 md:px-10 md:pt-32 lg:px-24"
    >
      <div className="mx-auto mt-12 grid w-full max-w-7xl grid-cols-1 items-center gap-10 sm:mt-16 sm:gap-12 md:mt-24 md:grid-cols-2 md:gap-16">
        {/* Left Side */}
        <div className="space-y-4 text-center md:text-left">
          {/* Heading */}
          <div>
            <motion.h1
              className="landing-heading text-4xl leading-tight text-foreground sm:text-5xl md:text-6xl"
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
              className="landing-heading text-4xl leading-tight text-primary sm:text-5xl md:text-6xl"
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
          <p className="mx-auto -mt-1 mb-8 max-w-md text-base leading-relaxed text-muted-foreground sm:mb-10 sm:text-lg md:mx-0">
            Plan your journey in advance with AI-powered delay predictions based
            on real traffic patterns in Delhi.
          </p>

          {/* Buttons */}
          <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:gap-4 md:justify-start">
            <Button
              asChild
              size="lg"
              className="landing-primary-button w-full justify-center px-6 py-5 text-base sm:w-auto sm:px-8 sm:py-6 sm:text-lg"
            >
              <Link to="/map">Get Started</Link>
            </Button>
            <Button
              asChild
              variant="ghost"
              size="lg"
              className="landing-hover-lift w-full justify-center px-6 py-5 text-base sm:w-auto sm:px-8 sm:py-6 sm:text-lg"
            >
              <Link to="/map">View Map</Link>
            </Button>
          </div>
        </div>

        {/* Right Side - Stats Card */}
        <div className="mx-auto w-full max-w-sm rounded-2xl bg-secondary p-5 text-foreground shadow-2xl sm:max-w-md sm:p-6 md:max-w-none">
          <p className="text-xs tracking-widest text-muted-foreground uppercase">
            Route and Prediction
          </p>
          <div>
            <p className="landing-heading text-3xl sm:text-4xl">12m Delay</p>
            <p className="mt-1 text-sm text-muted-foreground">
              High Congestion at ITO
            </p>
          </div>
          <div className="border-t border-border pt-4">
            <p className="text-xs tracking-widest text-muted-foreground uppercase">
              Confidence Score
            </p>
            <p className="landing-heading mt-1 text-4xl text-primary sm:text-5xl">
              94.4%
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
