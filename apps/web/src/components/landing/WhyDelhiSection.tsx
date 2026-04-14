import whyDelhiImage from "@/assets/why-delhi.jpg";
import { motion } from "motion/react";
import {
  fadeUp,
  landingViewport,
  staggerContainer,
} from "@/components/landing/motion";

export function WhyDelhiSection() {
  return (
    <motion.section
      id="why-delhi"
      className="relative overflow-hidden scroll-mt-24 py-8 md:py-12"
      initial="hidden"
      whileInView="visible"
      viewport={landingViewport}
      variants={staggerContainer(0.08, 0.14)}
    >
      <div className="mx-auto w-full max-w-6xl px-6">
        <motion.div className="mb-6 text-center md:mb-8" variants={fadeUp(24, 0.65)}>
          <h2 className="text-sm font-medium uppercase tracking-[0.2em] text-muted-foreground">
            Why Delhi ?
          </h2>
        </motion.div>

        <div className="grid items-center gap-8 md:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] md:gap-12">
          <motion.div
            className="group relative min-h-[260px] overflow-hidden rounded-[32px] shadow-lg shadow-zinc-100 md:min-h-[340px]"
            variants={fadeUp(36, 0.75)}
            whileHover={{ y: -6 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
          >
            <img
              src={whyDelhiImage}
              alt="Why Delhi"
              className="absolute inset-0 block h-full w-full scale-[1.15] object-cover object-[center_100%] transition-transform delay-200 duration-500 ease-out group-hover:scale-100"
            />
            <div className="absolute inset-0 bg-black/35 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
            <div className="pointer-events-none absolute inset-0 flex items-end p-6 opacity-0 transition-opacity delay-200 duration-300 group-hover:opacity-100 md:p-8">
              <p className="text-2xl font-semibold leading-tight tracking-tight text-white md:text-4xl">
                A City Where Time
                <br />
                is Unpredictable.
              </p>
            </div>
          </motion.div>

          <motion.div
            className="flex flex-col gap-6 text-left"
            variants={staggerContainer(0.14, 0.12)}
          >
            <div className="space-y-5">
              <motion.div className="space-y-1" variants={fadeUp(22, 0.6)}>
                <h3 className="text-lg font-semibold text-black md:text-xl">
                  Massive Daily Commuter Load
                </h3>
                <p className="max-w-md text-[0.85rem] leading-relaxed text-black/80 md:text-[1rem]">
                  Delhi handles over 14 million public transit trips daily. The
                  sheer volume makes every route unpredictable without
                  intelligent prediction systems.
                </p>
              </motion.div>

              <motion.div className="space-y-1" variants={fadeUp(22, 0.6)}>
                <h3 className="text-lg font-semibold text-black md:text-xl">
                  Peak Hour Chaos
                </h3>
                <p className="max-w-md text-[0.85rem] leading-relaxed text-black/80 md:text-[1rem]">
                  The same route can vary by 20–40 minutes depending on time of
                  day, season, or local events like festivals and VIP
                  movements.
                </p>
              </motion.div>

              <motion.div className="space-y-1" variants={fadeUp(22, 0.6)}>
                <h3 className="text-lg font-semibold text-black md:text-xl">
                  No Predictive Visibility
                </h3>
                <p className="max-w-md text-[0.85rem] leading-relaxed text-black/80 md:text-[1rem]">
                  Current apps only show live traffic, not tomorrow&apos;s
                  delays. RouteMinds fills this gap with ML-powered future
                  predictions.
                </p>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.section>
  );
}
