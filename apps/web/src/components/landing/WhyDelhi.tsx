import delhiTraffic from "@/assets/bradyn-trollip-TiPYSWJqWCM-unsplash.jpg"
import {motion} from "motion/react"

const container = {
  hidden: {opacity: 0},
  visible: {opacity: 1, transition: {staggerChildren: 0.2, delayChildren: 0.15}},
};

const item = {
  hidden: {opacity: 0, y: 20},
  visible: {opacity: 1, y: 0},
  transition: {
      duration: 5,
      ease: [0.25, 0.1, 0.25, 1] 
    },
};


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
    <section id="why-delhi"
      style={{ fontFamily: "Bespoke Slab, sans-serif", fontWeight: 400 }}
      className="bg-white px-8 md:px-16 lg:px-24 py-24"
    >
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-16 items-center">

        {/* Left - Image */}
        <div className="relative rounded-2xl overflow-hidden shadow-lg">
          <img
            src={delhiTraffic}
            alt="Delhi Traffic"
            className="w-full h-[350px] object-cover hover:scale-110 transition-transform duration-500"
          />
          <div className="absolute bottom-6 left-6 bg-white/90 backdrop-blur-sm rounded-xl px-4 py-3 shadow-md">
            <p className="text-xs text-gray-400 uppercase tracking-widest">Daily Commuters</p>
            <p className="text-2xl font-bold text-[#1a1a1a]">14M+</p>
          </div>
        </div>

        {/* Right - Content */}
        <div className="space-y-10">
          <div>
            <p className="text-xs tracking-widest uppercase text-[#8B7D3A] font-semibold mb-3" >
              Why Delhi?
            </p>
            <h2 className="text-4xl md:text-5xl font-bold text-[#1a1a1a] leading-tight" style={{ fontFamily: " Poppins , sans-serif", fontWeight: 600 }}>
              A City Where Time <br />
              <span className="text-[#8B7D3A]">is Unpredictable.</span>
            </h2>
          </div>

          <motion.div className="space-y-8" variants={container} initial="hidden" whileInView="visible" viewport={{ once: false,  margin: "-50px"  }} style={{ listStyle: "none" }}>
            {reasons.map((reason) => (
              <motion.div key={reason.number} className="flex gap-6 items-start" variants={item} >
                <span className="text-3xl font-bold text-gray-300 leading-none flex-shrink-0"  >
                  {reason.number}
                </span>
                <div>
                  <h3 className="text-base font-bold text-[#1a1a1a] mb-1" >
                    {reason.title}
                  </h3>
                  <p className="text-[#555] text-sm leading-relaxed" >
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