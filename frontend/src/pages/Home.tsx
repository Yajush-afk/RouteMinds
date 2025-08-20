import FeatureSection from "@/components/FeatureSection";
import HeroSection from "@/components/HeroSection";
import MainLayout from "@/components/layout/MainLayout";
function Home() {
  return (
    <MainLayout>
      <HeroSection />
      <FeatureSection />
    </MainLayout>
  );
}

export default Home;
