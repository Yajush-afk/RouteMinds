import paperTexture from "@/assets/Paper Texture@2x.png";
import featurePlaceholder from "@/assets/background-2x.png";
import { motion } from "motion/react";
import {
  fadeIn,
  fadeUp,
  landingViewport,
  staggerContainer,
} from "@/components/landing/motion";

const featureCards = [
  {
    heading: "AI Delay Prediction",
    subheading: "Prediction Stack",
    description:
      "Estimate likely delays ahead of time using segment-level travel-time modeling. The prediction flow is trained on consecutive stop-event segments with temporal, route, and rolling-delay context, then exposed through segment prediction APIs that can be used directly for route scoring.",
  },
  {
    heading: "Smarter Route Selection",
    subheading: "Routing Engine",
    description:
      "Choose routes using predicted travel cost instead of static shortest distance. The routing layer builds a transit graph from GTFS stops, trips, routes, and stop times, then runs Dijkstra optimization over predicted segment travel-time costs based on origin, destination, and query time.",
  },
  {
    heading: "Real-Time Transit Context",
    subheading: "Realtime Signals",
    description:
      "Keep decisions current by enriching routes with live operational updates. GTFS-RT vehicle positions continuously refresh delay context through realtime backend endpoints, and that delay enrichment feeds into downstream routing decisions so recommendations stay practical in changing traffic.",
  },
];

export function FeaturesSection() {
  return (
    <motion.section
      id="features"
      className="relative z-10 -mt-12 scroll-mt-24 overflow-hidden py-20 md:-mt-14 md:py-24"
      initial="hidden"
      whileInView="visible"
      viewport={landingViewport}
      variants={staggerContainer(0.08, 0.14)}
    >
      <motion.div
        className="pointer-events-none absolute inset-0 z-0 bg-linear-to-b from-transparent via-background/80 to-background"
        variants={fadeIn(0.7)}
      />
      <motion.div className="pointer-events-none absolute inset-0 z-10" variants={fadeIn(0.8, 0.1)}>
        <motion.img
          src={paperTexture}
          alt=""
          aria-hidden="true"
          className="absolute left-1/2 top-20 hidden w-[150vw] max-w-none -translate-x-1/2 mix-blend-screen opacity-45 md:block md:top-32 md:w-[min(1400px,110vw)]"
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 0.45, y: 0 }}
          viewport={landingViewport}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
      </motion.div>

      <div className="relative z-20 mx-auto w-full max-w-6xl px-6">
        <motion.div className="mb-10 space-y-3 text-center md:mb-12" variants={fadeUp(28, 0.7)}>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-muted-foreground">
            Features
          </p>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            Built for daily commuters.
          </h2>
        </motion.div>

        <motion.div
          className="mx-auto flex w-full max-w-5xl flex-col gap-10"
          variants={staggerContainer(0.14, 0.16)}
        >
          {featureCards.map((card, index) => (
            <motion.div
              key={card.heading}
              className="grid items-center gap-6 md:grid-cols-2 md:gap-8"
              variants={fadeUp(34, 0.7)}
            >
              <motion.article
                className={`group overflow-hidden rounded-[32px] border border-border bg-card shadow-lg shadow-zinc-100 ${
                  index === 1 ? "md:order-2" : ""
                }`}
                whileHover={{ y: -6 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
              >
                <img
                  src={featurePlaceholder}
                  alt=""
                  aria-hidden="true"
                  className="aspect-[5/3] w-full scale-[1.15] object-cover transition-transform delay-200 duration-500 ease-out group-hover:scale-100"
                />
              </motion.article>

              <motion.div
                className={index === 1 ? "md:order-1" : "md:order-2"}
                variants={fadeUp(24, 0.65)}
              >
                <h3 className="text-2xl font-semibold tracking-tight text-card-foreground md:text-3xl">
                  {card.heading}
                </h3>
                <p className="mt-2 text-sm font-medium uppercase tracking-[0.18em] text-foreground/75">
                  {card.subheading}
                </p>
                <p className="mt-4 max-w-prose text-base text-foreground/80">
                  {card.description}
                </p>
              </motion.div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </motion.section>
  );
}
