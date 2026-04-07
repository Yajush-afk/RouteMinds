import { useRef } from "react"

const features = [
  {
    tag: "Route Rationalization",
    heading: "Dynamic routing powered by ML-predicted travel times.",
    description:
      "Optimizes routes based on machine learning predicted segment travel times — not static shortest distance. The system continuously updates cost estimates per road segment, enabling decisions that reflect real-world conditions rather than map geometry alone.",
    image: "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800&q=80&auto=format&fit=crop",
    imageAlt: "City road network aerial view",
    reverse: false,
  },
  {
    tag: "Delay Prediction",
    heading: "XGBoost-trained models that see delays before they happen.",
    description:
      "An XGBoost-based segment travel-time model trained on GTFS schedules and simulated delay data. It learns temporal and spatial patterns across the transit network to forecast where and when delays will occur with high accuracy.",
    image: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80&auto=format&fit=crop",
    imageAlt: "Data visualization and analytics dashboard",
    reverse: true,
  },
  {
    tag: "Route Selection",
    heading: "Dijkstra-based optimization over predicted segment costs.",
    description:
      "Applies Dijkstra's algorithm over a live transit graph where each edge weight reflects the predicted cost of traversal. This ensures the selected route is optimal against future conditions, not just current snapshot data.",
    image: "https://images.unsplash.com/photo-1569336415962-a4bd9f69cd83?w=800&q=80&auto=format&fit=crop",
    imageAlt: "Metro transit map and routes",
    reverse: false,
  },
  {
    tag: "Real-time Enrichment",
    heading: "Live vehicle positions injected directly into routing decisions.",
    description:
      "Ingests GTFS-RT vehicle position feeds to capture live segment delays and inject that context into every routing computation. Routes are recalculated on the fly as new position data streams in, keeping decisions anchored to what is actually happening on the ground.",
    image: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80&auto=format&fit=crop",
    imageAlt: "Real-time data streams and live monitoring",
    reverse: true,
  },
]

export default function FeaturesSection() {
  const sectionRef = useRef<HTMLElement>(null)

  return (
    <section
      id="features"
      ref={sectionRef}
      className="bg-white px-4 py-16 sm:px-6 sm:py-20 md:px-10 lg:px-24"
    >
      <div className="mx-auto max-w-7xl ">

        {/* Section header */}
        <div className="mb-20 flex flex-col items-center text-center sm:mb-28">
          <p className="font-body mb-4 text-xs font-semibold tracking-widest text-[#5a2d14] uppercase">
            What We Offer
          </p>
          <h2 className="font-heading mb-4 whitespace-nowrap text-3xl leading-tight text-foreground sm:text-4xl md:text-5xl">
            Travel Smarter, Not Harder.
          </h2>
          <p className="font-body max-w-md text-base leading-relaxed text-muted-foreground">
            Our ML engine processes thousands of real-time data points to keep Delhi moving efficiently.
          </p>
        </div>

        {/* Alternating feature rows */}
        <div className="flex flex-col gap-28 sm:gap-36">
          {features.map((feature) => (
            <div
              key={feature.tag}
              className={`flex flex-col gap-12 md:flex-row md:items-center md:gap-20 ${
                feature.reverse ? "md:flex-row-reverse" : ""
              }`}
            >
              {/* Image */}
              <div className="flex flex-col gap-20 md:gap-36 w-full md:w-[52%]">
                <div className="overflow-hidden rounded-[20px] gap-20 border border-zinc-300">
                  <img
                    src={feature.image}
                    alt={feature.imageAlt}
                    className="h-72 w-full object-cover sm:h-80 md:h-[380px]"
                    loading="lazy"
                  />
                </div>
              </div>

              {/* Content */}
              {/* Content */}
<div className="w-full md:w-[48%]">
  <div className="max-w-sm">
    {/* Tag */}
    <p className="font-body mb-5 text-xs font-semibold tracking-widest text-[#5a2d14] uppercase">
      {feature.tag}
    </p>

    {/* Heading */}
    <h3 className="font-heading mb-6 text-[20px] leading-snug text-foreground">
      {feature.heading}
    </h3>

    {/* Description */}
    <p className="font-body text-[16px] leading-relaxed text-muted-foreground">
      {feature.description}
    </p>
  </div>
</div>
            </div>
          ))}
        </div>

      </div>
    </section>
  )
}