import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

function HeroSection() {
  return (
    <>
      <div className="px-4 flex flex-col items-center mt-6 lg:mt-20">
        <h1 className="text-4xl sm:text-6xl lg:text-7xl text-center tracking-wide">
          OptiBus Built for{" "}
          <span className=" block bg-gradient-to-r from-green-500 to-blue-800 text-transparent bg-clip-text">
            Smarter Mobility.
          </span>
        </h1>
        <p className="mt-10 text-lg text-center text-neutral-500 max-w-3xl">
          An AI-driven system that predicts delays in Delhi’s public bus system
          and suggests optimized scheduling to reduce bunching and passenger
          waiting time.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center my-10">
          <Link to={"/sign-up"}>
            <Button size="lg">Get Started</Button>
          </Link>
          <Link to={"/learn-more"}>
            <Button size="lg" variant="outline">
              Learn More
            </Button>
          </Link>
        </div>
      </div>
    </>
  );
}

export default HeroSection;
