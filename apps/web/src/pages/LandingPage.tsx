//import { Link } from "react-router-dom"
import Navbar from "@/components/landing/Navbar"
import HeroSection from "@/components/landing/HeroSection"
import FeaturesSection from "@/components/landing/FeaturesSection"
import WhyDelhi from "@/components/landing/WhyDelhi"
import FAQSection from "@/components/landing/FAQSection"
import Footer from "@/components/landing/Footer"

// function LandingPage() {
//   return (
//     <main className="grid min-h-screen place-items-center bg-background px-6 text-center">
//       <div className="space-y-4">
//         <h1 className="text-3xl font-semibold text-foreground sm:text-4xl">
//           Route Minds Landing Page
//         </h1>
//         <Link className="text-primary underline underline-offset-4" to="/map">
//           Go to map
//         </Link>
//       </div>
//     </main>
//   )
// }

export default function LandingPage() {
  return (
    <main className="landing-theme bg-background text-foreground">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <WhyDelhi />
      <FAQSection />
      <Footer />
    </main>
  )
}
