
import { Link } from "react-router-dom"
import {motion} from "motion/react"

export default function HeroSection() {
  return (
    <section id="about"
    style={{ fontFamily: "'Poppins', sans-serif" }}
    className="bg-[#F5F5F0] px-8 md:px-16 lg:px-24 flex flex-col justify-start pt-28 pb-20"    >
        <div className="max-w-7xl mx-auto w-full grid grid-cols-1 md:grid-cols-2 gap-16 items-center mt-24">
        
        {/* Left Side */}
        <div className="space-y-3">
  

          {/* Heading */}
          <div>
            <motion.h1 
            className="text-5xl md:text-6xl font-bold text-[#1a1a1a] leading-tight"
            initial={{opacity:0, x: -40}}
            whileInView={{opacity:1, x: 0}}
            transition={{duration: 0.8, ease:"easeInOut"}}
            >
              Stop Waiting.
            </motion.h1>
            <motion.h1 
            className="text-5xl md:text-6xl font-bold text-[#8B7D3A] leading-tight"
            initial={{opacity:0, x: -40}}
            whileInView={{opacity:1, x: 0}}
            transition={{duration: 0.8, ease:"easeInOut"}}
            >
              Start Predicting.
            </motion.h1>
          </div>

          {/* Description */}
          <p className="text-[#555] text-lg max-w-md leading-relaxed -mt-2 mb-10" style={{ fontFamily: "Bespoke Slab, sans-serif", fontWeight: 400}}>
            Plan your journey in advance with AI-powered delay predictions
            based on real traffic patterns in Delhi.
          </p>

          {/* Buttons */}
          <div className="flex items-center gap-4" style={{ fontFamily: "Bespoke Slab, sans-serif",  }}>
            <Link
              to="/map"
              className="bg-[#1a1a1a] text-white px-6 py-3 rounded-md font-semibold flex items-center gap-2 hover:bg-[#333] transition-colors"
            >
              Try Demo →
            </Link>
            <Link
              to="/map"
              className="text-[#1a1a1a] font-semibold underline underline-offset-4 hover:text-[#8B7D3A] transition-colors"
            >
              View Map
            </Link>
          </div>
        </div>

        {/* Right Side - Stats Card */}
        <div className="bg-[#1a1a1a] rounded-2xl p-6 text-white space-y-6 shadow-2xl" style={{ fontFamily: "Bespoke Slab, sans-serif" }}>
          <p className="text-xs tracking-widest uppercase text-gray-400">
            Route and Prediction
          </p>
          <div>
            <p className="text-4xl font-bold" style={{ fontFamily: " Poppins , sans-serif", fontWeight: 600 }}>12m Delay</p>
            <p className="text-gray-400 text-sm mt-1">High Congestion at ITO</p>
          </div>
          <div className="border-t border-gray-700 pt-4">
            <p className="text-xs tracking-widest uppercase text-gray-400">
              Confidence Score
            </p>
            <p className="text-5xl font-bold text-blue-400 mt-1" style={{ fontFamily: " Poppins , sans-serif", fontWeight: 600 }}>94.4%</p>
          </div>
        </div>

      </div>
    </section>
  )
}