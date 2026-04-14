import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { motion } from "motion/react";
import {
  fadeUp,
  landingViewport,
  staggerContainer,
} from "@/components/landing/motion";

const faqItems = [
  {
    question: "How does RouteMinds predict delays?",
    answer:
      "It analyzes historical traffic data, peak hours, and route patterns to estimate delays for the next day using our ML model trained on Delhi-specific road data.",
  },
  {
    question: "Is the prediction accurate?",
    answer:
      "The model is designed around Delhi-specific traffic behavior and route history, so it performs best when enough route and timing data are available. Accuracy improves as more trip data is incorporated.",
  },
  {
    question: "Does it show real-time tracking?",
    answer:
      "RouteMinds combines predictive routing with real-time transit context, so you can factor in current movement signals while still planning ahead instead of reacting only to live traffic.",
  },
  {
    question: "Which routes does RouteMinds currently cover?",
    answer:
      "The current focus is Delhi public transit workflows, especially routes where delay prediction and time-based route choice can make a practical difference for daily commuters.",
  },
  {
    question: "Is RouteMinds available for private vehicles too?",
    answer:
      "The current product direction is centered on public transit planning. Private-vehicle support would require a different optimization layer and is not the primary use case right now.",
  },
];

export function FaqSection() {
  return (
    <motion.section
      id="faq"
      className="scroll-mt-24 py-10 md:py-14"
      initial="hidden"
      whileInView="visible"
      viewport={landingViewport}
      variants={staggerContainer(0.08, 0.12)}
    >
      <div className="mx-auto max-w-3xl px-6">
        <motion.div className="mb-10 text-center sm:mb-12" variants={fadeUp(24, 0.65)}>
          <h2 className="text-sm font-medium uppercase tracking-[0.2em] text-muted-foreground">
            FAQ
          </h2>
        </motion.div>

        <motion.div variants={fadeUp(30, 0.7)}>
          <Accordion defaultValue={["faq-0"]} className="w-full">
            <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-lg shadow-zinc-100">
            {faqItems.map((item, index) => (
              <AccordionItem
                key={item.question}
                value={`faq-${index}`}
                className="border-b-0 px-0 not-last:border-b-0"
              >
                <AccordionTrigger className="rounded-xl px-6 py-5 text-base font-medium text-black hover:no-underline sm:text-lg">
                  <span className="pr-6">{item.question}</span>
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-5 pt-0 text-sm leading-relaxed text-black/70 sm:text-base">
                  {item.answer}
                </AccordionContent>
                {index < faqItems.length - 1 ? (
                  <div className="h-px w-full bg-border" />
                ) : null}
              </AccordionItem>
            ))}
            </div>
          </Accordion>
        </motion.div>
      </div>
    </motion.section>
  );
}
