import { FaqSection } from "@/components/landing/FAQSection"
import { FeaturesSection } from "@/components/landing/FeaturesSection"
import { HeroSection } from "@/components/landing/HeroSection"
import { LandingFooter } from "@/components/landing/LandingFooter"
import { LandingNavbar } from "@/components/landing/LandingNavbar"
import { WhyDelhiSection } from "@/components/landing/WhyDelhiSection"

export function LandingPage() {
  return (
    <>
      <LandingNavbar />
      <HeroSection />
      <FeaturesSection />
      <WhyDelhiSection />
      <FaqSection />
      <LandingFooter />
    </>
  )
}

export default LandingPage
