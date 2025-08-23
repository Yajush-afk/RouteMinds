import { features } from "@/constants/features";

const FeatureSection = () => {
  return (
    <div className="relative mt-20 border-border min-h-[800px] bg-background transition-all">
      {/* Header Section */}
      <div className="text-center max-w-4xl mx-auto px-4">
        <span className="bg-primary text-slate-950 rounded-full h-6 text-sm font-medium px-3 py-1.5 uppercase tracking-wide">
          Feature
        </span>
        <h2 className="text-3xl sm:text-5xl lg:text-6xl mt-10 lg:mt-20 tracking-wide text-foreground font-bold">
          All new{" "}
          <span className="bg-gradient-to-r from-primary to-accent text-transparent bg-clip-text">
            Features
          </span>
        </h2>
      </div>

      {/* Features Grid */}
      <div className="max-w-7xl mx-auto mt-10 lg:mt-20 px-4 sm:px-8 lg:px-20">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
          {features.map((feature, index) => (
            <div key={index} className="group">
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 text-center sm:text-left p-6 rounded-lg border border-border/50 bg-card hover:bg-card/80 hover:border-primary/30 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
                {/* Icon Container */}
                <div className="flex-shrink-0 flex justify-center items-center h-12 w-12 bg-primary/10 text-primary rounded-full border border-primary/20 group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary transition-all duration-300 group-hover:scale-105">
                  <feature.icon className="w-5 h-5" />
                </div>

                {/* Content */}
                <div className="flex flex-col">
                  <h3 className="text-xl font-semibold mb-2 text-card-foreground group-hover:text-primary transition-colors duration-300">
                    {feature.label}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed group-hover:text-card-foreground transition-colors duration-300">
                    {feature.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FeatureSection;