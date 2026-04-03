import { Link } from "react-router-dom"
import {motion} from "motion/react"

export default function Navbar() {
  return (
    <nav
     style={{ fontFamily: "'Poppins', sans-serif" }}
     className="fixed top-4 left-4 right-4 z-50 bg-white/70 backdrop-blur-md border border-gray-200/50  px-8 py-4 flex items-center justify-between shadow-sm rounded-2xl"    >
      {/* Logo */}
      <Link to="/" className="text-[#1a1a1a] text-xl font-bold tracking-tight">
        RouteMinds
      </Link>

      {/* Nav Links */}
      <div className="hidden md:flex items-center gap-6">
  <a href="#about" className="text-[#1a1a1a] text-base  hover:text-[#8B7D3A] transition-colors">About</a>
  <a href="#features" className="text-[#1a1a1a] text-base  hover:text-[#8B7D3A] transition-colors">Features</a>
   <a href="#why-delhi" className="text-[#1a1a1a] text-base  hover:text-[#8B7D3A] transition-colors">Why Delhi?</a>
  <a href="#faqs" className="text-[#1a1a1a] text-base  hover:text-[#8B7D3A] transition-colors">FAQs</a>
</div>

      {/* Sign Up Button */}
      <Link to='/signup'>
      <motion.button
      whileHover={{scale: 1.05, y: -1}}
      whileTap={{scale: 0.9, y: 1}}
      transition={{type:"spring"}}
        className="bg-[#1a1a1a] text-white text-sm font-semibold px-5 py-2.5 rounded-md hover:bg-[#333] transition-colors"
      >
        Sign Up
      </motion.button>
      </Link>
    </nav>
  )
}