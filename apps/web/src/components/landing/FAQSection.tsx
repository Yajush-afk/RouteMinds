import { useState } from "react"
import { ChevronDown } from "lucide-react"

const faqs = [
  {
    question: "How does RouteMinds predict delays?",
    answer:
      "It analyzes historical traffic data, peak hours, and route patterns to estimate delays for the next day using our ML model trained on Delhi-specific road data.",
  },
  {
    question: "Is the prediction accurate?",
    answer:
      "Predictions are based on real patterns and provide a strong estimate with 94%+ accuracy, though exact times may vary slightly depending on unexpected events.",
  },
  {
    question: "Does it show real-time tracking?",
    answer:
      "No, RouteMinds focuses on predicting future delays rather than live tracking. It tells you what to expect before you leave, not just what's happening right now.",
  },
  {
    question: "Which routes does RouteMinds currently cover?",
    answer:
      "RouteMinds currently covers major DTC bus routes across Delhi NCR, with a focus on high-traffic corridors like ITO, Connaught Place, and key metro interchange points.",
  },
  {
    question: "Is RouteMinds available for private vehicles too?",
    answer:
      "Currently RouteMinds is optimized for public transit routes in Delhi. Support for private vehicle routing is on our roadmap and will be available in a future update.",
  },
]

export default function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null)

  const toggle = (index: number) => {
    setOpenIndex(openIndex === index ? null : index)
  }

  return (
    <section id="faqs"
      style={{ fontFamily: "'Syne', sans-serif" }}
      className="bg-[#F5F5F0] px-8 md:px-16 lg:px-24 py-24"
    >
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <p className="text-xs tracking-widest uppercase text-[#8B7D3A] font-semibold mb-3">
            Got Questions?
          </p>
          <h2 className="text-4xl md:text-5xl font-bold text-[#1a1a1a]">
            Frequently Asked Questions
          </h2>
          <div className="w-10 h-1 bg-[#8B7D3A] mx-auto mt-4 rounded-full"></div>
        </div>

        {/* FAQ Items */}
        <div className="space-y-3">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className="bg-white border border-gray-100 shadow-sm overflow-hidden"
            >
              <button
                onClick={() => toggle(index)}
                className="w-full flex items-center justify-between px-6 py-5 text-left"
              >
                <span className="text-[#1a1a1a] font-semibold text-base">
                  {faq.question}
                </span>
                <ChevronDown
                  className={`w-5 h-5 text-[#8B7D3A] transition-transform duration-300 flex-shrink-0 ml-4 ${
                    openIndex === index ? "rotate-180" : ""
                  }`}
                />
              </button>
              {openIndex === index && (
                <div className="px-6 pb-5">
                  <p className="text-[#555] text-sm leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}