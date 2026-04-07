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
      className="bg-white px-4 py-16 sm:px-6 sm:py-20 md:px-10 lg:px-24"
    >
      <div className="mx-auto grid max-w-7xl grid-cols-1 items-center gap-10 sm:gap-12 md:grid-cols-2 md:gap-16">
        {/* Left - Image */}
        <div className="relative overflow-hidden rounded-2xl shadow-lg">
          <img
            src={delhiTraffic}
            alt="Delhi Traffic"
            loading="lazy"
            decoding="async"
            className="h-64 w-full object-cover transition-transform duration-500 sm:h-80 md:h-[350px] md:hover:scale-110"
          />
          <div className="absolute bottom-4 left-4 rounded-xl bg-background/90 px-3 py-2 shadow-md backdrop-blur-sm sm:bottom-6 sm:left-6 sm:px-4 sm:py-3">
            <p className=" font-body text-xs tracking-widest text-muted-foreground uppercase">
              Daily Commuters
            </p>
            <p className="font-heading  text-xl text-foreground sm:text-2xl">
              14M+
            </p>
          </div>
        </div>

        {/* Right - Content */}
        <div className="space-y-8 sm:space-y-10">
          <div>
            <p className="font-body mb-3 text-xs font-semibold tracking-widest text-[#5a2d14] uppercase">
              Why Delhi?
            </p>
            <h2 className="font-heading  text-3xl leading-tight text-foreground sm:text-4xl md:text-5xl">
              A City Where Time <br />
              <span className="text-[#5a2d14]">is Unpredictable.</span>
            </h2>
          </div>

          <motion.div
            className="list-none space-y-6 sm:space-y-8"
            variants={container}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, margin: "-50px" }}
          >
            {reasons.map((reason) => (
              <motion.div
                key={reason.number}
                className="flex items-start gap-4 sm:gap-6"
                variants={item}
              >
                <span className="font-heading shrink-0 text-2xl leading-none font-bold text-border sm:text-3xl">
                  {reason.number}
                </span>
                <div>
                  <h3 className="font-heading font-semibold mb-1 text-base text-foreground">
                    {reason.title}
                  </h3>
                  <p className="font-body text-sm leading-relaxed text-muted-foreground">
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
