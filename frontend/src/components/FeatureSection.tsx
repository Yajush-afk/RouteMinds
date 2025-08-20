import CardComponent from "./CardComponent";

function FeatureSection() {
  return (<>
    <div className="relative mt-10 border-b border-neutral-700/80 min-h-[800px]">
      <div className="text-center">
        <span className="bg-neutral-900 text-orange-500 rounded-full h-6 text-lg font-medium px-2 py-1 uppercase">
          Features
        </span>
        <h2 className="mt-4 text-3xl font-bold">Our Amazing Features</h2>
      </div>
      <CardComponent />
      <CardComponent />
      <CardComponent />

    </div>
  </>
  );
}

export default FeatureSection;
