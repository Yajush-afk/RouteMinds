import { Brain, Clock, Route, TrendingUp } from "lucide-react"
import { cn } from "@workspace/ui/lib/utils"

const features = [
  {
    title: "Route Rationalization",
    description:
      "Dynamic route optimization based on ML-predicted segment travel times rather than static shortest distance.",
    icon: <Route className="h-6 w-6" />,
  },
  {
    title: "Delay Prediction",
    description:
      "XGBoost-based segment travel-time prediction model trained on GTFS and simulated delay data.",
    icon: <Clock className="h-6 w-6" />,
  },
  {
    title: "Route Selection",
    description:
      "Dijkstra-based route optimization using predicted segment costs over a transit graph.",
    icon: <Brain className="h-6 w-6" />,
  },
  {
    title: "Real-time Enrichment",
    description:
      "GTFS-RT vehicle position ingestion with live segment delay context injection into routing decisions.",
    icon: <TrendingUp className="h-6 w-6" />,
  },
]

const Feature = ({
  title,
  description,
  icon,
  index,
}: {
  title: string
  description: string
  icon: React.ReactNode
  index: number
}) => {
  return (
    <div
      className={cn(
        "flex flex-col py-10 px-8 relative group/feature border-border transition-colors duration-200",
        // right border for left column items
        index % 2 === 0 && "md:border-r",
        // top border for bottom row items
        index >= 2 && "border-t",
      )}
    >
      {/* Full-box hover background */}
{/* Full-box hover background */}
<div className="opacity-0 group-hover/feature:opacity-100 transition duration-200 absolute inset-0 bg-gradient-to-br from-[#fef3c7]/50 to-transparent pointer-events-none" />
      {/* Icon */}
      <div className="mb-4 relative z-10 text-[#5a2d14]">
        {icon}
      </div>

      {/* Title with animated left bar */}
      <div className="text-base font-semibold mb-3 relative z-10">
        <div className="absolute -left-8 inset-y-0 h-6 group-hover/feature:h-8 w-1 rounded-tr-full rounded-br-full bg-border group-hover/feature:bg-[#5a2d14] transition-all duration-200 origin-center" />
        <span className="group-hover/feature:translate-x-2 transition duration-200 inline-block font-heading text-foreground">
          {title}
        </span>
      </div>

      {/* Description */}
      <p className="font-body text-sm leading-relaxed text-muted-foreground max-w-xs relative z-10">
        {description}
      </p>
    </div>
  )
}

export default function FeaturesSectionGrid() {
  return (
    <section
      id="features"
      className="bg-white px-4 py-16 sm:px-6 sm:py-20 md:px-10 lg:px-24"
    >
      <div className="mx-auto max-w-7xl">

        {/* Section header */}
        <div className="mb-20 flex flex-col items-center text-center sm:mb-28">
          <p className="font-body mb-4 text-xs font-semibold tracking-widest text-[#5a2d14] uppercase">
            What We Offer
          </p>
          <h2 className="font-heading mb-4 whitespace-nowrap text-4xl   sm:text-4xl md:text-5xl">
            Travel Smarter, Not Harder.
          </h2>
          <p className="font-body max-w-md text-lg leading-relaxed text-muted-foreground">
            Our ML engine processes thousands of real-time data points to keep Delhi moving efficiently.
          </p>
        </div>

        {/* Grid wrapped in border box */}
        <div className="border border-border rounded-2xl overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-2">
            {features.map((feature, index) => (
              <Feature key={feature.title} {...feature} index={index} />
            ))}
          </div>
        </div>

      </div>
    </section>
  )
}