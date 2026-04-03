import Navbar from "@/components/landing/Navbar"
import HeroSection from "@/components/landing/HeroSection"
import FeaturesSection from "@/components/landing/FeaturesSection"
import WhyDelhi from "@/components/landing/WhyDelhi"
import FAQSection from "@/components/landing/FAQSection"
import Footer from "@/components/landing/Footer"

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
