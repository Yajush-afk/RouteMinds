import { Brain, Route, Clock, MapPin, TrendingUp, Shield } from "lucide-react"

export default function FeaturesSection() {
  return (
    <section id="features"
      style={{ fontFamily: "'Syne', sans-serif" }}
      className="bg-white px-8 md:px-16 lg:px-24 py-24"
    >
      {/* Header */}
      <div className="max-w-7xl mx-auto">
        <p className="text-xs tracking-widest uppercase text-[#8B7D3A] font-semibold mb-3">
          What We Offer
        </p>
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-4">
          <h2 className="text-4xl md:text-5xl font-bold text-[#1a1a1a] leading-tight max-w-lg">
            Travel Smarter,<br /> Not Harder.
          </h2>
          <p className="text-[#555] max-w-sm text-base leading-relaxed">
            Our ML engine processes thousands of real-time data points to keep
            Delhi moving efficiently.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

          {/* Large - Delay Prediction */}
          <div className="md:col-span-2 bg-white rounded-2xl p-8 flex flex-col justify-between min-h-[220px] border border-gray-100 shadow-sm">
            <div className="bg-[#F5F5F0] w-10 h-10 rounded-xl flex items-center justify-center">
              <Clock className="text-[#8B7D3A] w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#1a1a1a] mb-2">Delay Prediction</h3>
              <p className="text-[#555] text-sm leading-relaxed">
                Estimate tomorrow's delays using historical traffic data and seasonal patterns unique to Delhi's road network.
              </p>
            </div>
          </div>

          {/* Small - Real-Time Traffic */}
          <div className="bg-[#1a1a1a] rounded-2xl p-8 flex flex-col justify-between min-h-[220px]">
            <div className="bg-white/10 w-10 h-10 rounded-xl flex items-center justify-center">
              <TrendingUp className="text-white w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-2">Real-Time Traffic Analysis</h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                Continuously monitors live road conditions and adjusts predictions instantly.
              </p>
            </div>
          </div>

          {/* Small - Road Parameter */}
          <div className="bg-[#8B7D3A] rounded-2xl p-8 flex flex-col justify-between min-h-[220px]">
            <div className="bg-white/20 w-10 h-10 rounded-xl flex items-center justify-center">
              <MapPin className="text-white w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-2">Road Parameter Monitoring</h3>
              <p className="text-yellow-100 text-sm leading-relaxed">
                Tracks road closures, construction zones and weather impact on routes.
              </p>
            </div>
          </div>

          {/* Large - Multi-Route */}
          <div className="md:col-span-2 bg-white rounded-2xl p-8 flex flex-col justify-between min-h-[220px] border border-gray-100 shadow-sm">
            <div className="bg-[#F5F5F0] w-10 h-10 rounded-xl flex items-center justify-center">
              <Route className="text-[#8B7D3A] w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#1a1a1a] mb-2">Multi-Route Rationalization</h3>
              <p className="text-[#555] text-sm leading-relaxed">
                Balances traffic load across multiple routes to reduce city-wide congestion and ensure optimal distribution.
              </p>
            </div>
          </div>

          {/* Small - Smart Suggestions */}
          <div className="bg-white rounded-2xl p-8 flex flex-col justify-between min-h-[220px] border border-gray-100 shadow-sm">
            <div className="bg-[#F5F5F0] w-10 h-10 rounded-xl flex items-center justify-center">
              <Brain className="text-[#8B7D3A] w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#1a1a1a] mb-2">Smart Suggestions</h3>
              <p className="text-[#555] text-sm leading-relaxed">
                Get the best route based on predicted congestion and real-time variables.
              </p>
            </div>
          </div>

          {/* Small - Historical Learning */}
          <div className="md:col-span-2 bg-[#1a1a1a] rounded-2xl p-8 flex flex-col justify-between min-h-[220px]">
            <div className="bg-white/10 w-10 h-10 rounded-xl flex items-center justify-center">
              <Shield className="text-white w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-2">Historical Pattern Learning</h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                ML model continuously learns from past traffic data to improve future predictions with every passing day.
              </p>
            </div>
          </div>

        </div>
      </div>
    </section>
  )
}