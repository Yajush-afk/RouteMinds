import { Activity, ArrowRight, MapPin, Route } from "lucide-react";
import { motion } from "motion/react";
import { Link } from "react-router-dom";
import heroImage from "@/assets/image.png";

const highlights = [
  {
    icon: Route,
    label: "Route optimization with predicted segment travel time",
  },
  {
    icon: Activity,
    label: "Live delay context from GTFS-RT vehicle positions",
  },
  {
    icon: MapPin,
    label: "Delhi-focused map workflow with search and geocoding",
  },
];

export function HeroSection() {
  return (
    <main className="relative isolate flex min-h-[88svh] items-center overflow-hidden">
      <motion.div
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: `url(${heroImage})` }}
        initial={{ scale: 1.08, opacity: 0.7 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      />
      <motion.div
        className="absolute inset-0 bg-black/55"
        initial={{ opacity: 0.75 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />
      <motion.div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-44 bg-linear-to-b from-transparent via-background/70 to-background md:h-56"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.8, ease: "easeOut" }}
      />

      <div className="relative z-10 mx-auto w-full max-w-5xl px-6 py-24 md:py-28">
        <motion.div
          className="flex flex-col items-center space-y-6 text-center"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: {
              transition: {
                staggerChildren: 0.14,
                delayChildren: 0.2,
              },
            },
          }}
        >
          <motion.div
            className="space-y-4"
            variants={{
              hidden: { opacity: 0, y: 28 },
              visible: {
                opacity: 1,
                y: 0,
                transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] },
              },
            }}
          >
            <motion.h1 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight text-white sm:text-4xl md:text-5xl">
              Stop Waiting.
              <br />
              Start Predicting.
            </motion.h1>
            <motion.p className="mx-auto max-w-2xl text-base text-white/80 sm:text-lg">
              Plan your journey in advance with AI-powered delay predictions
              based on real traffic patterns in Delhi.
            </motion.p>
          </motion.div>

          <motion.ul
            className="grid w-full max-w-4xl gap-3 text-left sm:grid-cols-3"
            variants={{
              hidden: {},
              visible: {
                transition: {
                  staggerChildren: 0.12,
                  delayChildren: 0.15,
                },
              },
            }}
          >
            {highlights.map(({ icon: Icon, label }) => (
              <motion.li
                key={label}
                className="rounded-xl border border-white/25 bg-black/25 p-3 text-sm text-white/85 backdrop-blur-[1px] transition duration-300 hover:-translate-y-1 hover:bg-black/35 hover:shadow-[0_16px_35px_-18px_rgba(0,0,0,0.7)]"
                variants={{
                  hidden: { opacity: 0, y: 22 },
                  visible: {
                    opacity: 1,
                    y: 0,
                    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
                  },
                }}
                whileHover={{ y: -6 }}
              >
                <div className="mb-2 inline-flex rounded-lg bg-white/15 p-2">
                  <Icon className="size-4 text-white" />
                </div>
                <p>{label}</p>
              </motion.li>
            ))}
          </motion.ul>

          <motion.div
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: {
                opacity: 1,
                y: 0,
                transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] },
              },
            }}
          >
            <Link
              to="/map"
              className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-medium text-black transition hover:bg-white/90"
            >
              Get started
              <ArrowRight className="size-4" />
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </main>
  );
}
