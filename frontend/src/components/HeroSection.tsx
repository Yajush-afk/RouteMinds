import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

function HeroSection() {
  return (
    <div className="px-4 flex flex-col items-center mt-6 lg:mt-20">
      <div className="max-w-5xl mx-auto text-center">
        {/* Main Heading */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl tracking-wide font-bold leading-tight">
          OptiBus Built for{" "}
          <span className="block bg-gradient-to-r from-green-500 to-blue-800 text-transparent bg-clip-text">
            Smarter Mobility.
          </span>
        </h1>
        
        {/* Description */}
        <p className="mt-8 lg:mt-10 text-lg lg:text-xl text-center text-muted-foreground max-w-3xl mx-auto leading-relaxed">
          An AI-driven system that predicts delays in Delhi's public bus system
          and suggests optimized scheduling to reduce bunching and passenger
          waiting time.
        </p>
        
        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center mt-8 lg:mt-10">
          <Link to="/sign-up">
            <Button 
              size="lg" 
              className="w-full sm:w-auto px-8 py-3 text-lg font-semibold hover:scale-105 transition-transform duration-200"
            >
              Get Started
            </Button>
          </Link>
          <Link to="/learn-more">
            <Button 
              size="lg" 
              variant="outline"
              className="w-full sm:w-auto px-8 py-3 text-lg font-semibold hover:scale-105 transition-transform duration-200 hover:bg-neutral-900 hover:text-white"
            >
              Learn More
            </Button>
          </Link>
        </div>
        
        {/* Optional: Trust indicators or features */}
        <div className="mt-16 lg:mt-20">
          <p className="text-sm text-muted-foreground mb-6">Trusted by transport authorities</p>
          <div className="flex flex-wrap justify-center items-center gap-8 opacity-60">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm text-neutral-400">Real-time AI Predictions</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-neutral-400">Optimized Scheduling</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
              <span className="text-sm text-neutral-400">Reduced Wait Times</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HeroSection;