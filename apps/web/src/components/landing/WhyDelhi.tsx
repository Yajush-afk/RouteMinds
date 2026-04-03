import delhiTraffic from "@/assets/bradyn-trollip-TiPYSWJqWCM-unsplash-optimized.jpg"
import { motion } from "motion/react"

const container = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.2, delayChildren: 0.15 },
  },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
  transition: {
    duration: 5,
    ease: [0.25, 0.1, 0.25, 1],
  },
}

const reasons = [
  {
    number: "01",
    title: "Massive Daily Commuter Load",
    description:
      "Delhi handles over 14 million public transit trips daily. The sheer volume makes every route unpredictable without intelligent prediction systems.",
  },
  {
    number: "02",
    title: "Peak Hour Chaos",
    description:
      "The same route can vary by 20–40 minutes depending on time of day, season, or local events like festivals and VIP movements.",
  },
  {
    number: "03",
    title: "No Predictive Visibility",
    description:
      "Current apps only show live traffic — not tomorrow's delays. RouteMinds fills this gap with ML-powered future predictions.",
  },
]

export default function WhyDelhiSection() {
  return (
    <section
      id="why-delhi"
      className="bg-background px-8 py-24 md:px-16 lg:px-24"
    >
      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-16 md:grid-cols-2">
        {/* Left - Image */}
        <div className="relative overflow-hidden rounded-2xl shadow-lg">
          <img
            src={delhiTraffic}
            alt="Delhi Traffic"
            loading="lazy"
            decoding="async"
            className="h-[350px] w-full object-cover transition-transform duration-500 hover:scale-110"
          />
          <div className="absolute bottom-6 left-6 rounded-xl bg-background/90 px-4 py-3 shadow-md backdrop-blur-sm">
            <p className="text-xs tracking-widest text-muted-foreground uppercase">
              Daily Commuters
            </p>
            <p className="landing-heading text-2xl text-foreground">14M+</p>
          </div>
        </div>

        {/* Right - Content */}
        <div className="space-y-10">
          <div>
            <p className="mb-3 text-xs font-semibold tracking-widest text-primary uppercase">
              Why Delhi?
            </p>
            <h2 className="landing-heading text-4xl leading-tight text-foreground md:text-5xl">
              A City Where Time <br />
              <span className="text-primary">is Unpredictable.</span>
            </h2>
          </div>

          <motion.div
            className="list-none space-y-8"
            variants={container}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: "-50px" }}
          >
            {reasons.map((reason) => (
              <motion.div
                key={reason.number}
                className="flex items-start gap-6"
                variants={item}
              >
                <span className="flex-shrink-0 text-3xl leading-none font-bold text-border">
                  {reason.number}
                </span>
                <div>
                  <h3 className="landing-heading mb-1 text-base text-foreground">
                    {reason.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {reason.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
