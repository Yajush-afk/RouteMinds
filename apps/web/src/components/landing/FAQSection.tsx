import { Fragment } from "react"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@workspace/ui/components/accordion"
import { Separator } from "@workspace/ui/components/separator"

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
  return (
    <section
      id="faqs"
      className="bg-background px-4 py-16 sm:px-6 sm:py-20 md:px-10 lg:px-24"
    >
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-10 text-center sm:mb-12">
          <p className="mb-3 text-xs font-semibold tracking-widest text-primary uppercase">
            Got Questions?
          </p>
          <h2 className="landing-heading text-3xl text-foreground sm:text-4xl md:text-5xl">
            Frequently Asked Questions
          </h2>
          <div className="mx-auto mt-4 h-1 w-10 rounded-full bg-primary"></div>
        </div>

        {/* FAQ Items */}
        <Accordion type="single" collapsible>
          {faqs.map((faq, index) => (
            <Fragment key={faq.question}>
              <AccordionItem
                value={`item-${index}`}
                className="border-b-0 not-last:border-b-0"
              >
                <AccordionTrigger className="landing-heading rounded-xl text-base sm:text-lg">
                  {faq.question}
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed sm:text-base">
                  {faq.answer}
                </AccordionContent>
              </AccordionItem>
              {index < faqs.length - 1 && <Separator />}
            </Fragment>
          ))}
        </Accordion>
      </div>
    </section>
  )
}
