import { Brain, Route, Clock, MapPin, TrendingUp, Shield, ChevronLeft, ChevronRight } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { AnimatePresence, motion } from "motion/react"

const features = [
  {
    icon: <Clock className="w-6 h-6 text-[#8B7D3A]" />,
    title: "Delay Prediction",
    description: "Estimate tomorrow's delays using historical traffic data and seasonal patterns unique to Delhi's road network.",
  },
  {
    icon: <TrendingUp className="w-6 h-6 text-[#8B7D3A]" />,
    title: "Real-Time Traffic Analysis",
    description: "Continuously monitors live road conditions and adjusts route predictions instantly across Delhi's road network.",

  },
  {
    icon: <MapPin className="w-6 h-6 text-[#8B7D3A]" />,
    title: "Road Parameter Monitoring",
    description: "Tracks road closures, construction zones, VIP movements and weather impact on routes in real time.",
  },
  {
    icon: <Route className="w-6 h-6 text-[#8B7D3A]" />,
    title: "Multi-Route Rationalization",
    description: "Balances traffic load across multiple routes to reduce city-wide congestion and ensure optimal distribution.",
  },
  {
    icon: <Brain className="w-6 h-6 text-[#8B7D3A]" />,
    title: "Smart Suggestions",
    description: "Get the best route based on predicted congestion, real-time variables and your travel history.",

  },
  {
    icon: <Shield className="w-6 h-6 text-[#8B7D3A]" />,
    title: "Historical Pattern Learning",
    description: "ML model continuously learns from past traffic data to improve future predictions with every passing day.",
  },
]

export default function FeaturesSection() {
  const [current, setCurrent] = useState(0)
  const [direction, setDirection] = useState(1)
  const [isInView, setIsInView] = useState(false)
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => setIsInView(entry.isIntersecting),
      { threshold: 0.3 }
    )
    if (sectionRef.current) observer.observe(sectionRef.current)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!isInView) return
    const interval = setInterval(() => {
      setDirection(1)
      setCurrent((prev) => (prev + 1) % features.length)
    }, 2500)
    return () => clearInterval(interval)
  }, [isInView])

  function goNext() {
    setDirection(1)
    setCurrent((prev) => (prev + 1) % features.length)
  }

  function goPrev() {
    setDirection(-1)
    setCurrent((prev) => (prev - 1 + features.length) % features.length)
  }

  const feature = features[current]

  return (
    <section
      id="features"
      ref={sectionRef}
      style={{ fontFamily: "'Syne', sans-serif" }}
      className="bg-white px-8 md:px-16 lg:px-24 py-20"
    >
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <p className="text-xs tracking-widest uppercase text-[#8B7D3A] font-semibold mb-3">
          What We Offer
        </p>
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-3 gap-4">
          <h2 className="text-4xl md:text-5xl font-bold text-[#1a1a1a] leading-tight max-w-lg">
            Travel Smarter,<br /> Not Harder.
          </h2>
        </div>
        <p className="text-[#555] max-w-sm text-base leading-relaxed mb-12">
            Our ML engine processes thousands of real-time data points to keep Delhi moving efficiently.
          </p>

        {/* Carousel */}
        <div className="flex items-center gap-4">

          {/* Prev Button */}
          <button
            onClick={goPrev}
            className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center hover:border-[#8B7D3A] hover:text-[#8B7D3A] transition-colors flex-shrink-0"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {/* Card */}
          <div className="flex-1 overflow-hidden">
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={current}
                custom={direction}
                initial={{ opacity: 0, x: direction * 60 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: direction * -60 }}
                transition={{ type: "spring", visualDuration: 0.4, bounce: 0.2 }}
                className="bg-[#F5F5F0] rounded-2xl p-8 min-h-[200px] flex flex-col justify-between border border-gray-100"
              >
                {/* Top row */}
                <div className="flex items-start justify-between">
                  <div className="bg-white w-11 h-11 rounded-xl flex items-center justify-center shadow-sm">
                    {feature.icon}
                  </div>
                </div>

                {/* Bottom row */}
                <div className="mt-6">
                  <h3 className="text-xl font-bold text-[#1a1a1a] mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-[#555] text-sm leading-relaxed max-w-xl">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Next Button */}
          <button
            onClick={goNext}
            className="w-10 h-10 rounded-full border border-gray-200 flex items-center justify-center hover:border-[#8B7D3A] hover:text-[#8B7D3A] transition-colors flex-shrink-0"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

        </div>

        {/* Dots */}
        <div className="flex justify-center gap-2 mt-6">
          {features.map((_, i) => (
            <button
              key={i}
              onClick={() => {
                setDirection(i > current ? 1 : -1)
                setCurrent(i)
              }}
              className={`h-2 rounded-full transition-all duration-300 ${
                i === current ? "bg-[#8B7D3A] w-6" : "bg-gray-300 w-2"
              }`}
            />
          ))}
        </div>

      </div>
    </section>
  )
}