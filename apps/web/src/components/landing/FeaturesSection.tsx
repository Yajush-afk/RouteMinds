import {
  Brain,
  ChevronLeft,
  ChevronRight,
  Clock,
  MapPin,
  Route,
  Shield,
  TrendingUp,
} from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useReducedMotion } from "motion/react"

import { Button } from "@workspace/ui/components/button"
import {
  Carousel,
  type CarouselApi,
  CarouselContent,
  CarouselItem,
} from "@workspace/ui/components/carousel"
import { cn } from "@workspace/ui/lib/utils"

const features = [
  {
    icon: <Clock className="h-6 w-6 text-primary" />,
    title: "Delay Prediction",
    description:
      "Estimate tomorrow's delays using historical traffic data and seasonal patterns unique to Delhi's road network.",
  },
  {
    icon: <TrendingUp className="h-6 w-6 text-primary" />,
    title: "Real-Time Traffic Analysis",
    description:
      "Continuously monitors live road conditions and adjusts route predictions instantly across Delhi's road network.",
  },
  {
    icon: <MapPin className="h-6 w-6 text-primary" />,
    title: "Road Parameter Monitoring",
    description:
      "Tracks road closures, construction zones, VIP movements and weather impact on routes in real time.",
  },
  {
    icon: <Route className="h-6 w-6 text-primary" />,
    title: "Multi-Route Rationalization",
    description:
      "Balances traffic load across multiple routes to reduce city-wide congestion and ensure optimal distribution.",
  },
  {
    icon: <Brain className="h-6 w-6 text-primary" />,
    title: "Smart Suggestions",
    description:
      "Get the best route based on predicted congestion, real-time variables and your travel history.",
  },
  {
    icon: <Shield className="h-6 w-6 text-primary" />,
    title: "Historical Pattern Learning",
    description:
      "ML model continuously learns from past traffic data to improve future predictions with every passing day.",
  },
]

export default function FeaturesSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const shouldReduceMotion = useReducedMotion()
  const [api, setApi] = useState<CarouselApi>()
  const [current, setCurrent] = useState(0)
  const [isInView, setIsInView] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)")
    const updateIsMobile = () => setIsMobile(mediaQuery.matches)

    updateIsMobile()
    mediaQuery.addEventListener("change", updateIsMobile)

    return () => mediaQuery.removeEventListener("change", updateIsMobile)
  }, [])

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setIsInView(entry.isIntersecting),
      { threshold: 0.3 }
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!api) return

    const updateCurrent = () => {
      setCurrent(api.selectedScrollSnap())
    }

    updateCurrent()
    api.on("select", updateCurrent)
    api.on("reInit", updateCurrent)

    return () => {
      api.off("select", updateCurrent)
      api.off("reInit", updateCurrent)
    }
  }, [api])

  useEffect(() => {
    if (!api || !isInView || shouldReduceMotion || isPaused || isMobile) return

    const interval = window.setInterval(() => {
      api.scrollNext()
    }, 2500)

    return () => window.clearInterval(interval)
  }, [api, isInView, shouldReduceMotion, isPaused, isMobile])

  return (
    <section
      id="features"
      ref={sectionRef}
      className="bg-secondary px-4 py-16 sm:px-6 sm:py-20 md:px-10 lg:px-24"
    >
      <div className="mx-auto max-w-7xl">
        <p className="mb-3 text-xs font-semibold tracking-widest text-primary uppercase">
          What We Offer
        </p>
        <div className="mb-3 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <h2 className="landing-heading max-w-lg text-3xl leading-tight text-foreground sm:text-4xl md:text-5xl">
            Travel Smarter,
            <br /> Not Harder.
          </h2>
        </div>
        <p className="mb-8 max-w-md text-base leading-relaxed text-muted-foreground sm:mb-12">
          Our ML engine processes thousands of real-time data points to keep
          Delhi moving efficiently.
        </p>

        <Carousel
          setApi={setApi}
          opts={{ align: "start", loop: true }}
          className="w-full"
        >
          <CarouselContent>
            {features.map((feature) => (
              <CarouselItem key={feature.title}>
                <div
                  className="flex min-h-[240px] flex-col justify-between rounded-2xl border border-border bg-background p-5 sm:min-h-[220px] sm:p-6 md:min-h-50 md:p-8"
                  onMouseEnter={() => setIsPaused(true)}
                  onMouseLeave={() => setIsPaused(false)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary shadow-sm sm:h-11 sm:w-11">
                      {feature.icon}
                    </div>
                  </div>

                  <div className="mt-5 sm:mt-6">
                    <h3 className="landing-heading mb-2 text-lg text-foreground sm:text-xl">
                      {feature.title}
                    </h3>
                    <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
        </Carousel>

        <div className="mt-4 flex items-center justify-between gap-3 sm:mt-6">
          <Button
            type="button"
            variant="outline"
            size="icon-lg"
            onClick={() => api?.scrollPrev()}
            className="shrink-0 rounded-xl border-border bg-background text-muted-foreground shadow-none hover:border-primary hover:bg-background hover:text-primary"
            aria-label="Previous feature"
          >
            <ChevronLeft />
          </Button>

          <div className="flex flex-1 justify-center gap-2">
            {features.map((feature, index) => (
              <Button
                key={feature.title}
                type="button"
                variant="ghost"
                size="icon-xs"
                onClick={() => api?.scrollTo(index)}
                aria-label={`Go to ${feature.title}`}
                className={cn(
                  "h-2 min-w-0 rounded-xl px-0 transition-all duration-300 hover:bg-primary/20",
                  current === index
                    ? "w-6 bg-primary hover:bg-primary/90"
                    : "w-2 bg-border"
                )}
              />
            ))}
          </div>

          <Button
            type="button"
            variant="outline"
            size="icon-lg"
            onClick={() => api?.scrollNext()}
            className="shrink-0 rounded-xl border-border bg-background text-muted-foreground shadow-none hover:border-primary hover:bg-background hover:text-primary"
            aria-label="Next feature"
          >
            <ChevronRight />
          </Button>
        </div>
      </div>
    </section>
  )
}
