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
    if (!api || !isInView || shouldReduceMotion || isPaused) return

    const interval = window.setInterval(() => {
      api.scrollNext()
    }, 2500)

    return () => window.clearInterval(interval)
  }, [api, isInView, shouldReduceMotion, isPaused])

  return (
    <section
      id="features"
      ref={sectionRef}
      className="bg-secondary px-8 py-20 md:px-16 lg:px-24"
    >
      <div className="mx-auto max-w-7xl">
        <p className="mb-3 text-xs font-semibold tracking-widest text-primary uppercase">
          What We Offer
        </p>
        <div className="mb-3 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <h2 className="landing-heading max-w-lg text-4xl leading-tight text-foreground md:text-5xl">
            Travel Smarter,
            <br /> Not Harder.
          </h2>
        </div>
        <p className="mb-12 max-w-sm text-base leading-relaxed text-muted-foreground">
          Our ML engine processes thousands of real-time data points to keep
          Delhi moving efficiently.
        </p>

        <div className="flex items-center gap-4">
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

          <Carousel
            setApi={setApi}
            opts={{ align: "start", loop: true }}
            className="flex-1"
          >
            <CarouselContent>
              {features.map((feature) => (
                <CarouselItem key={feature.title}>
                  <div
                    className="flex min-h-[200px] flex-col justify-between rounded-2xl border border-border bg-background p-8"
                    onMouseEnter={() => setIsPaused(true)}
                    onMouseLeave={() => setIsPaused(false)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-secondary shadow-sm">
                        {feature.icon}
                      </div>
                    </div>

                    <div className="mt-6">
                      <h3 className="landing-heading mb-2 text-xl text-foreground">
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

        <div className="mt-6 flex justify-center gap-2">
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
      </div>
    </section>
  )
}
