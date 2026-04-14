import type { MouseEvent } from "react";
import { FaGithub } from "react-icons/fa";
import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { fadeIn, fadeUp } from "@/components/landing/motion";

function getSectionOffset(sectionId: string) {
  return sectionId === "why-delhi" ? 24 : 80;
}

export function LandingNavbar() {
  const handleSectionClick =
    (sectionId: string) => (event: MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault();

      const target = document.getElementById(sectionId);
      if (!target) {
        return;
      }

      const targetTop =
        target.getBoundingClientRect().top +
        window.scrollY +
        getSectionOffset(sectionId);

      window.scrollTo({ top: targetTop, behavior: "smooth" });
    };

  return (
    <motion.header
      className="pointer-events-none absolute inset-x-0 top-4 z-50"
      initial="hidden"
      animate="visible"
      variants={fadeIn(0.55)}
    >
      <motion.nav
        className="pointer-events-auto relative mx-auto flex w-[min(92%,64rem)] flex-col gap-3 rounded-3xl px-4 py-3 md:flex-row md:items-center md:justify-between md:rounded-4xl md:px-5"
        variants={fadeUp(18, 0.65)}
      >
        <motion.div
          className="flex w-full items-center justify-between md:w-auto md:justify-start"
          variants={fadeUp(16, 0.55)}
        >
          <Link
            to="/"
            className="text-xl font-semibold tracking-tight text-white sm:text-2xl"
          >
            RouteMinds
          </Link>

          <div className="flex items-center gap-2 text-sm md:hidden">
            <a
              href="https://github.com/yajush-afk/routeminds"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-black px-3 py-2 text-sm font-medium text-white transition hover:bg-black/90"
            >
              <FaGithub className="size-4" />
              <span className="hidden sm:inline">GitHub</span>
            </a>
            <Link
              to="/map"
              className="inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-medium text-black transition hover:bg-white/90"
            >
              SignUp
            </Link>
          </div>
        </motion.div>

        <motion.div
          className="hidden absolute left-1/2 -translate-x-1/2 items-center gap-1 md:flex"
          variants={fadeUp(16, 0.55)}
        >
          <a
            href="/#features"
            onClick={handleSectionClick("features")}
            className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Features
          </a>
          <a
            href="/#why-delhi"
            onClick={handleSectionClick("why-delhi")}
            className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Why Delhi
          </a>
          <a
            href="/#faq"
            onClick={handleSectionClick("faq")}
            className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            FAQ
          </a>
        </motion.div>

        <motion.div
          className="hidden w-full items-center gap-1 overflow-x-auto text-sm md:hidden"
          variants={fadeUp(16, 0.55)}
        >
          <a
            href="/#features"
            onClick={handleSectionClick("features")}
            className="inline-flex shrink-0 items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Features
          </a>
          <a
            href="/#why-delhi"
            onClick={handleSectionClick("why-delhi")}
            className="inline-flex shrink-0 items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            Why Delhi
          </a>
          <a
            href="/#faq"
            onClick={handleSectionClick("faq")}
            className="inline-flex shrink-0 items-center rounded-lg px-3 py-2 text-sm font-medium text-white transition hover:text-white/80"
          >
            FAQ
          </a>
        </motion.div>

        <motion.div
          className="hidden items-center gap-2 text-sm md:flex"
          variants={fadeUp(16, 0.55)}
        >
          <a
            href="https://github.com/yajush-afk/routeminds"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-black/90"
          >
            <FaGithub className="size-4" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
          <Link
            to="/map"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-white/90"
          >
            SignUp
          </Link>
        </motion.div>
      </motion.nav>
    </motion.header>
  );
}
