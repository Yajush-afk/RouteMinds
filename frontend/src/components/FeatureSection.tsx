import { features } from "@/constants/features";

const FeatureSection = () => {
  return (
    <div className="relative mt-20 border-b border-neutral-800 min-h-[800px]">
      <div className="text-center">
        <span className="bg-neutral-900 text-orange-500 rounded-full h-6 text-sm font-medium px-2 py-1 uppercase">
          Feature
        </span>
        <h2 className="text-3xl sm:text-5xl lg:text-6xl mt-10 lg:mt-20 tracking-wide">
          All new{" "}
          <span className="bg-gradient-to-r from-orange-500 to-orange-800 text-transparent bg-clip-text">
            Features
          </span>
        </h2>
      </div>
      
      {/* Responsive Features Grid */}
      <div className="flex flex-wrap justify-center items-start mt-10 lg:mt-20 px-4 sm:px-8 lg:px-20">
        {features.map((feature, index) => (
          <div key={index} className="w-full sm:w-1/2 lg:w-1/3 p-4">
            <div className="flex flex-col sm:flex-row items-center sm:items-start gap-4 text-center sm:text-left">
              {/* Icon Container */}
              <div className="flex-shrink-0 flex justify-center items-center h-12 w-12 bg-neutral-900 text-orange-700 rounded-full">
                <feature.icon />
              </div>
              
              {/* Content */}
              <div className="flex flex-col">
                <h5 className="text-xl font-medium mb-2">{feature.label}</h5>
                <p className="text-md text-neutral-500 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FeatureSection;