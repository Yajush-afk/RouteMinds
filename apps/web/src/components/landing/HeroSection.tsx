import { Link } from "react-router-dom"
import { motion } from "motion/react"

import { Button } from "@workspace/ui/components/button"

export default function HeroSection() {
  return (
    <section
      id="about"
      className="bg-background px-8 pt-28 pb-20 md:px-16 lg:px-24"
    >
      <div className="mx-auto mt-24 grid w-full max-w-7xl grid-cols-1 items-center gap-16 md:grid-cols-2">
        {/* Left Side */}
        <div className="space-y-3">
          {/* Heading */}
          <div>
            <motion.h1
              className="landing-heading text-5xl leading-tight text-foreground md:text-6xl"
              initial={{ opacity: 0, x: -40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
            >
              Stop Waiting.
            </motion.h1>
            <motion.h1
              className="landing-heading text-5xl leading-tight text-primary md:text-6xl"
              initial={{ opacity: 0, x: -40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
            >
              Start Predicting.
            </motion.h1>
          </div>

          {/* Description */}
          <p className="-mt-2 mb-10 max-w-md text-lg leading-relaxed text-muted-foreground">
            Plan your journey in advance with AI-powered delay predictions based
            on real traffic patterns in Delhi.
          </p>

          {/* Buttons */}
          <div className="flex items-center gap-4">
            <Button
              asChild
              size="lg"
              className="landing-primary-button px-8 py-6 text-lg"
            >
              <Link to="/map">Get Started</Link>
            </Button>
            <Button
              asChild
              variant="ghost"
              size="lg"
              className="landing-hover-lift px-8 py-6 text-lg"
            >
              <Link to="/map">View Map</Link>
            </Button>
          </div>
        </div>

        {/* Right Side - Stats Card */}
        <div className="rounded-2xl bg-secondary p-6 text-foreground shadow-2xl">
          <p className="text-xs tracking-widest text-muted-foreground uppercase">
            Route and Prediction
          </p>
          <div>
            <p className="landing-heading text-4xl">12m Delay</p>
            <p className="mt-1 text-sm text-muted-foreground">
              High Congestion at ITO
            </p>
          </div>
          <div className="border-t border-border pt-4">
            <p className="text-xs tracking-widest text-muted-foreground uppercase">
              Confidence Score
            </p>
            <p className="landing-heading mt-1 text-5xl text-primary">94.4%</p>
          </div>
        </div>
      </div>
    </section>
  )
}
